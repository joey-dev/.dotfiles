"""Bubblewrap (bwrap) command builder for least-privilege stage sandboxing."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from claude_workflow.config import RepoAccess

_SYSTEM_RO_PATHS: tuple[str, ...] = (
    "/nix/store",
    "/run/current-system",
    "/etc",
    "/usr",
    "/bin",
    "/lib",
    "/lib64",
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


def _append_git_mask(cmd: list[str], repo_dir: Path) -> None:
    """Hide .git inside the sandbox using --tmpfs (dir) or --ro-bind /dev/null (worktree file)."""
    git_entry = repo_dir / ".git"
    if git_entry.is_file():
        cmd.extend(["--ro-bind", "/dev/null", str(git_entry)])
    elif git_entry.is_dir():
        cmd.extend(["--tmpfs", str(git_entry)])


def build_bwrap_command(spec: SandboxSpec, inner_cmd: Sequence[str]) -> list[str]:
    """Build a bubblewrap command line wrapping inner_cmd with least-privilege mounts."""
    cmd: list[str] = [
        "bwrap",
        "--die-with-parent",
        "--new-session",
        "--dev",
        "/dev",
        "--proc",
        "/proc",
        "--tmpfs",
        "/tmp",
    ]

    if not spec.allow_network:
        cmd.append("--unshare-net")

    for sys_path in _SYSTEM_RO_PATHS:
        if Path(sys_path).exists():
            cmd.extend(["--ro-bind", sys_path, sys_path])

    if spec.repo_dir is not None and spec.repo_access is not RepoAccess.NONE:
        bind_flag = "--bind" if spec.repo_access is RepoAccess.RW else "--ro-bind"
        repo_str = str(spec.repo_dir)
        cmd.extend([bind_flag, repo_str, repo_str])
        _append_git_mask(cmd, spec.repo_dir)

    state_str = str(spec.state_dir)
    cmd.extend(["--bind", state_str, state_str])

    if spec.kb_dir is not None and spec.kb_dir.exists():
        kb_str = str(spec.kb_dir)
        cmd.extend(["--ro-bind", kb_str, kb_str])

    for skill_dir in spec.skills_dirs:
        if skill_dir.exists():
            skill_str = str(skill_dir)
            cmd.extend(["--ro-bind", skill_str, skill_str])

    cmd.extend(["--chdir", str(spec.workdir), "--", *inner_cmd])
    return cmd
