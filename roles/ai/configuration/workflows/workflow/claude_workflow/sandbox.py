"""Bubblewrap (bwrap) command builder with isolated $HOME and least-privilege mounts."""

from __future__ import annotations

import os
import shutil
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from claude_workflow.config import RepoAccess

_SYSTEM_RO_PATHS: tuple[str, ...] = (
    "/nix/store",
    "/run/current-system",
    "/etc/profiles",
    "/etc/static",
    "/etc/resolv.conf",
    "/etc/ssl",
    "/etc/hosts",
    "/usr",
    "/bin",
    "/lib",
    "/lib64",
)

_SANDBOX_PROXY_SOCK = "/tmp/cw-proxy.sock"
_PROXY_BRIDGE_SCRIPT = (
    f"socat TCP-LISTEN:3128,bind=127.0.0.1,fork,reuseaddr "
    f"UNIX-CONNECT:{_SANDBOX_PROXY_SOCK} >/dev/null 2>&1 & "
    "SOCAT_PID=$!; "
    "trap 'kill $SOCAT_PID 2>/dev/null || true' EXIT; "
    "tries=0; "
    "until socat -T 1 /dev/null TCP:127.0.0.1:3128,connect-timeout=1 "
    ">/dev/null 2>&1; do "
    'tries=$((tries + 1)); if [ "$tries" -ge 20 ] || ! kill -0 "$SOCAT_PID"; then '
    "echo 'Workflow proxy bridge failed to start' >&2; exit 1; fi; sleep 0.1; done; "
    "export HTTPS_PROXY=http://127.0.0.1:3128 "
    "HTTP_PROXY=http://127.0.0.1:3128 "
    "NODE_USE_ENV_PROXY=1; "
    '"$@"'
)


@dataclass(frozen=True)
class SandboxSpec:
    """Filesystem and network isolation specification for a single stage."""

    repo_dir: Path | None
    repo_access: RepoAccess
    state_dir: Path
    skills_dirs: tuple[Path, ...]
    kb_dir: Path | None
    allow_network: bool
    workdir: Path
    mcp_config: Path | None = None
    flake_dir: Path | None = None
    proxy_socket: Path | None = None


@dataclass(frozen=True)
class SandboxPaths:
    """In-sandbox paths under the isolated $HOME."""

    home_dir: Path
    notes_dir: Path
    repo_dir: Path | None
    kb_dir: Path | None
    flake_dir: Path | None
    skills_dir: Path | None
    mcp_config: Path | None
    workdir: Path
    add_dirs: tuple[Path, ...]


def sandbox_paths(spec: SandboxSpec) -> SandboxPaths:
    """Compute clean $HOME-relative paths as seen inside the bwrap sandbox."""
    home = Path.home()
    notes_dir = home / "notes"

    repo_target: Path | None = None
    if spec.repo_dir is not None and spec.repo_access is not RepoAccess.NONE:
        repo_name = spec.repo_dir.resolve().name
        if repo_name in {"", "notes", "kb", "flake", ".claude", ".nix-profile"}:
            repo_name = "repository"
        repo_target = home / repo_name

    kb_target = home / "kb" if (spec.kb_dir is not None and spec.kb_dir.exists()) else None
    flake_target = (
        home / "flake" if (spec.flake_dir is not None and spec.flake_dir.exists()) else None
    )
    has_skills = any(s.exists() for s in spec.skills_dirs)
    skills_target = home / ".claude" / "skills" if has_skills else None
    mcp_target = (
        home / ".claude" / "mcp.json"
        if (spec.mcp_config is not None and spec.mcp_config.exists())
        else None
    )

    workdir = repo_target if repo_target is not None else notes_dir
    if spec.repo_dir is not None and repo_target is not None:
        relative_workdir = spec.workdir.resolve().relative_to(spec.repo_dir.resolve())
        workdir = repo_target / relative_workdir

    add_dirs: list[Path] = [notes_dir]
    if repo_target is not None and repo_target != workdir:
        add_dirs.append(repo_target)
    if kb_target is not None:
        add_dirs.append(kb_target)
    if flake_target is not None:
        add_dirs.append(flake_target)
    if skills_target is not None:
        add_dirs.append(skills_target)

    return SandboxPaths(
        home_dir=home,
        notes_dir=notes_dir,
        repo_dir=repo_target,
        kb_dir=kb_target,
        flake_dir=flake_target,
        skills_dir=skills_target,
        mcp_config=mcp_target,
        workdir=workdir,
        add_dirs=tuple(add_dirs),
    )


def prepare_sandbox_home(state_dir: Path) -> Path:
    """Create an isolated per-ticket $HOME and copy only .credentials.json (0600)."""
    sandbox_home = state_dir / "home"
    claude_dir = sandbox_home / ".claude"
    (claude_dir / "skills").mkdir(parents=True, exist_ok=True)
    os.chmod(claude_dir, 0o700)

    sandbox_creds = claude_dir / ".credentials.json"
    if sandbox_creds.is_symlink():
        raise RuntimeError(f"Sandbox credentials must not be a symlink: {sandbox_creds}")

    host_home = Path.home()
    host_creds = host_home / ".claude" / ".credentials.json"
    if not sandbox_creds.exists() and host_creds.is_file():
        shutil.copy2(host_creds, sandbox_creds)
        os.chmod(sandbox_creds, 0o600)

    host_claude_json = host_home / ".claude.json"
    sandbox_claude_json = sandbox_home / ".claude.json"
    if not sandbox_claude_json.exists() and host_claude_json.is_file():
        shutil.copy2(host_claude_json, sandbox_claude_json)
        os.chmod(sandbox_claude_json, 0o600)

    return sandbox_home


def _append_git_mask(cmd: list[str], host_repo: Path, sandbox_repo: Path) -> None:
    """Hide .git inside the sandbox using --tmpfs (dir) or --ro-bind /dev/null (worktree file)."""
    host_git = host_repo / ".git"
    sandbox_git = sandbox_repo / ".git"
    if host_git.is_file():
        cmd.extend(["--ro-bind", "/dev/null", str(sandbox_git)])
    elif host_git.is_dir():
        cmd.extend(["--tmpfs", str(sandbox_git)])


def build_bwrap_command(spec: SandboxSpec, inner_cmd: Sequence[str]) -> list[str]:
    """Build a bubblewrap command line wrapping inner_cmd with isolated $HOME and mounts."""
    paths = sandbox_paths(spec)
    sandbox_home_host = spec.state_dir / "home"

    cmd: list[str] = [
        "bwrap",
        "--die-with-parent",
        "--new-session",
        "--unshare-pid",
        "--dev",
        "/dev",
        "--proc",
        "/proc",
        "--tmpfs",
        "/tmp",
        "--tmpfs",
        "/home",
    ]

    if not spec.allow_network:
        cmd.append("--unshare-net")

    for sys_path in _SYSTEM_RO_PATHS:
        if Path(sys_path).exists():
            cmd.extend(["--ro-bind", sys_path, sys_path])

    if sandbox_home_host.exists():
        cmd.extend(["--bind", str(sandbox_home_host), str(paths.home_dir)])

    nix_profile = Path.home() / ".nix-profile"
    if nix_profile.exists():
        cmd.extend(["--ro-bind", str(nix_profile.resolve()), str(paths.home_dir / ".nix-profile")])

    host_settings = Path.home() / ".claude" / "settings.json"
    if host_settings.is_file() and sandbox_home_host.exists():
        cmd.extend(
            [
                "--ro-bind",
                str(host_settings),
                str(paths.home_dir / ".claude" / "settings.json"),
            ]
        )

    cmd.extend(["--bind", str(spec.state_dir), str(paths.notes_dir)])
    for name in ("state.json", ".lock"):
        if (spec.state_dir / name).is_file():
            cmd.extend(["--ro-bind", "/dev/null", str(paths.notes_dir / name)])
    if sandbox_home_host.is_dir():
        cmd.extend(["--tmpfs", str(paths.notes_dir / "home")])

    if spec.repo_dir is not None and paths.repo_dir is not None:
        bind_flag = "--bind" if spec.repo_access is RepoAccess.RW else "--ro-bind"
        cmd.extend([bind_flag, str(spec.repo_dir), str(paths.repo_dir)])
        _append_git_mask(cmd, spec.repo_dir, paths.repo_dir)

    if spec.kb_dir is not None and paths.kb_dir is not None:
        cmd.extend(["--ro-bind", str(spec.kb_dir), str(paths.kb_dir)])

    if spec.flake_dir is not None and paths.flake_dir is not None:
        cmd.extend(["--ro-bind", str(spec.flake_dir), str(paths.flake_dir)])

    if paths.skills_dir is not None:
        for skill_dir in spec.skills_dirs:
            if skill_dir.exists():
                cmd.extend(["--ro-bind", str(skill_dir), str(paths.skills_dir / skill_dir.name)])

    if spec.mcp_config is not None and paths.mcp_config is not None:
        cmd.extend(["--ro-bind", str(spec.mcp_config), str(paths.mcp_config)])

    wrapped_cmd: Sequence[str] = inner_cmd
    if spec.proxy_socket is not None:
        cmd.extend(["--bind", str(spec.proxy_socket), _SANDBOX_PROXY_SOCK])
        wrapped_cmd = ["sh", "-c", _PROXY_BRIDGE_SCRIPT, "cw-bridge", *inner_cmd]

    cmd.extend(["--chdir", str(paths.workdir), "--", *wrapped_cmd])
    return cmd
