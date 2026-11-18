"""Bubblewrap (bwrap) command builder with isolated $HOME and least-privilege mounts."""

from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from claude_workflow.config import RepoAccess
from claude_workflow.env import sandbox_env

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
    # (host folder, path relative to the repo) mounted read-only on top of the repo.
    repo_ro_overlays: tuple[tuple[Path, str], ...] = ()
    # (host path, path relative to $HOME) mounted read-only, e.g. CLAUDE.md.
    home_ro_mounts: tuple[tuple[Path, str], ...] = ()
    # Generated Claude settings, mounted read-only as ~/.claude/settings.json.
    settings_file: Path | None = None


@dataclass(frozen=True)
class SandboxPaths:
    """In-sandbox paths under the isolated $HOME."""

    home_dir: Path
    notes_dir: Path
    repo_dir: Path | None
    kb_dir: Path | None
    flake_dir: Path | None
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
    for host_path, relative in spec.home_ro_mounts:
        if host_path.is_dir():
            add_dirs.append(home / relative)

    return SandboxPaths(
        home_dir=home,
        notes_dir=notes_dir,
        repo_dir=repo_target,
        kb_dir=kb_target,
        flake_dir=flake_target,
        mcp_config=mcp_target,
        workdir=workdir,
        add_dirs=tuple(add_dirs),
    )


def _refuse_symlinks(*paths: Path) -> None:
    """The sandbox can write in its own $HOME, so it could plant symlinks there."""
    for path in paths:
        if path.is_symlink():
            raise RuntimeError(f"Refusing to use a symlink in the sandbox home: {path}")


def _safe_copy(source: Path, target: Path) -> None:
    """Copy source to target as a new 0600 file, never following links at the target.

    mkstemp creates a fresh file with a random name (O_EXCL), and os.replace swaps
    the target's directory entry, so a planted symlink is replaced, not written through.
    """
    fd, temporary = tempfile.mkstemp(dir=target.parent, prefix=".cw-copy-")
    try:
        with os.fdopen(fd, "wb") as output:
            output.write(source.read_bytes())
        os.replace(temporary, target)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise


def _token_expiry(path: Path) -> float | None:
    """Return claudeAiOauth.expiresAt from a credentials file, or None if unreadable."""
    try:
        data: object = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    oauth = cast(dict[str, object], data).get("claudeAiOauth")
    if not isinstance(oauth, dict):
        return None
    expires = cast(dict[str, object], oauth).get("expiresAt")
    return float(expires) if isinstance(expires, (int, float)) else None


def _copy_login_in(host: Path, sandbox: Path) -> None:
    """Give the sandbox the host login when it is missing or the host's lasts longer.

    One way only: the sandbox never writes back to the host, so a compromised
    stage cannot change your real login.
    """
    if not host.is_file():
        return
    if not sandbox.is_file():
        _safe_copy(host, sandbox)
        return
    host_expiry, sandbox_expiry = _token_expiry(host), _token_expiry(sandbox)
    if host_expiry is None:
        return  # unknown format: keep what the sandbox has
    if sandbox_expiry is None or host_expiry > sandbox_expiry:
        _safe_copy(host, sandbox)


def copy_mcp_auth_in(state_dir: Path) -> None:
    """Copy the mcp-remote login (~/.mcp-auth) into the sandbox home, one way.

    Per file: copied when it is missing in the sandbox or newer on the host.
    Host symlinks are skipped; symlinked folders in the sandbox are refused.
    The sandbox never writes back, so your host login can't be changed by a stage.
    """
    host_root = Path.home() / ".mcp-auth"
    sandbox_root = state_dir / "home" / ".mcp-auth"
    if host_root.is_symlink() or not host_root.is_dir():
        return
    for folder, _subfolders, files in os.walk(host_root):  # does not follow symlinks
        target_dir = sandbox_root / Path(folder).relative_to(host_root)
        _refuse_symlinks(state_dir / "home", sandbox_root, target_dir)
        target_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        for name in files:
            source, target = Path(folder) / name, target_dir / name
            if source.is_symlink() or not source.is_file():
                continue
            source_time = source.stat().st_mtime
            sandbox_is_current = (
                target.is_file()
                and not target.is_symlink()
                and target.stat().st_mtime >= source_time
            )
            if sandbox_is_current:
                continue  # the sandbox has the same or a newer (refreshed) copy
            _safe_copy(source, target)
            os.utime(target, (source_time, source_time))


def prepare_sandbox_home(state_dir: Path) -> Path:
    """Create an isolated per-ticket $HOME with your Claude login (0600)."""
    sandbox_home = state_dir / "home"
    claude_dir = sandbox_home / ".claude"
    sandbox_creds = claude_dir / ".credentials.json"
    sandbox_claude_json = sandbox_home / ".claude.json"
    _refuse_symlinks(sandbox_home, claude_dir, sandbox_creds)
    claude_dir.mkdir(parents=True, exist_ok=True)
    os.chmod(claude_dir, 0o700)

    host_home = Path.home()
    _copy_login_in(host_home / ".claude" / ".credentials.json", sandbox_creds)

    host_claude_json = host_home / ".claude.json"
    if host_claude_json.is_file() and (
        sandbox_claude_json.is_symlink() or not sandbox_claude_json.exists()
    ):
        _safe_copy(host_claude_json, sandbox_claude_json)

    return sandbox_home


def sandbox_settings(host_settings: Path) -> dict[str, object]:
    """Return the host Claude settings without hooks.

    The hooks call notify-send, which cannot work inside the sandbox (no D-Bus).
    Everything else, such as the permission deny rules, is kept.
    """
    if not host_settings.is_file():
        return {}
    settings = json.loads(host_settings.read_text(encoding="utf-8"))
    if not isinstance(settings, dict):
        return {}
    all_settings = cast(dict[str, object], settings)
    return {key: value for key, value in all_settings.items() if key != "hooks"}


def _append_git_mask(cmd: list[str], host_repo: Path, sandbox_repo: Path) -> None:
    """Hide .git inside the sandbox using --tmpfs (dir) or --ro-bind /dev/null (worktree file)."""
    host_git = host_repo / ".git"
    sandbox_git = sandbox_repo / ".git"
    if host_git.is_file():
        cmd.extend(["--ro-bind", "/dev/null", str(sandbox_git)])
    elif host_git.is_dir():
        cmd.extend(["--tmpfs", str(sandbox_git)])


def tiocsti_disabled() -> bool:
    """True when the kernel blocks TIOCSTI (typing into another process's terminal)."""
    try:
        return Path("/proc/sys/dev/tty/legacy_tiocsti").read_text().strip() == "0"
    except OSError:
        return False


def build_bwrap_command(
    spec: SandboxSpec,
    inner_cmd: Sequence[str],
    *,
    env: Mapping[str, str] | None = None,
    interactive: bool = False,
) -> list[str]:
    """Build a bubblewrap command line wrapping inner_cmd with isolated $HOME and mounts.

    env: the complete environment inside the sandbox. None means: build it from the
    host allowlist plus the flake's dev shell (see env.sandbox_env).

    interactive: keep the controlling terminal (no --new-session), so resizing and
    Ctrl-C work. Only done when the kernel already blocks TIOCSTI, the attack that
    --new-session protects against.
    """
    paths = sandbox_paths(spec)
    if env is None:
        flake = spec.flake_dir if spec.flake_dir and spec.flake_dir.exists() else None
        env = sandbox_env(flake)
    sandbox_home_host = spec.state_dir / "home"

    keep_terminal = interactive and tiocsti_disabled()
    if interactive and not keep_terminal:
        print("Warning: TIOCSTI enabled; interactive sandbox has no controlling terminal.")

    cmd: list[str] = ["bwrap", "--die-with-parent"]
    if not keep_terminal:
        cmd.append("--new-session")
    cmd += [
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

    # Start from an empty environment, so host secrets never reach the sandbox.
    cmd.append("--clearenv")
    for name, value in env.items():
        cmd.extend(["--setenv", name, value])

    for sys_path in _SYSTEM_RO_PATHS:
        if Path(sys_path).exists():
            cmd.extend(["--ro-bind", sys_path, sys_path])

    if sandbox_home_host.exists():
        cmd.extend(["--bind", str(sandbox_home_host), str(paths.home_dir)])

    nix_profile = Path.home() / ".nix-profile"
    if nix_profile.exists():
        cmd.extend(["--ro-bind", str(nix_profile.resolve()), str(paths.home_dir / ".nix-profile")])

    if spec.settings_file is not None and sandbox_home_host.exists():
        target = paths.home_dir / ".claude" / "settings.json"
        cmd.extend(["--ro-bind", str(spec.settings_file), str(target)])

    for host_path, relative in spec.home_ro_mounts:
        if host_path.exists():
            cmd.extend(["--ro-bind", str(host_path), str(paths.home_dir / relative)])

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
        for host_dir, relative in spec.repo_ro_overlays:
            cmd.extend(["--ro-bind", str(host_dir), str(paths.repo_dir / relative)])

    if spec.kb_dir is not None and paths.kb_dir is not None:
        cmd.extend(["--ro-bind", str(spec.kb_dir), str(paths.kb_dir)])

    if spec.flake_dir is not None and paths.flake_dir is not None:
        cmd.extend(["--ro-bind", str(spec.flake_dir), str(paths.flake_dir)])

    if spec.mcp_config is not None and paths.mcp_config is not None:
        cmd.extend(["--ro-bind", str(spec.mcp_config), str(paths.mcp_config)])

    wrapped_cmd: Sequence[str] = inner_cmd
    if spec.proxy_socket is not None:
        cmd.extend(["--bind", str(spec.proxy_socket), _SANDBOX_PROXY_SOCK])
        wrapped_cmd = ["sh", "-c", _PROXY_BRIDGE_SCRIPT, "cw-bridge", *inner_cmd]

    cmd.extend(["--chdir", str(paths.workdir), "--", *wrapped_cmd])
    return cmd
