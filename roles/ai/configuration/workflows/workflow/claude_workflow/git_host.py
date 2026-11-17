"""Host-side git worktree, diff, and commit helpers (never push/fetch/pull)."""

from __future__ import annotations

import subprocess
from collections.abc import Sequence
from pathlib import Path


class GitError(RuntimeError):
    """Raised when a host git command fails."""


def _run_git(
    cwd: Path,
    args: Sequence[str],
    *,
    allowed_returncodes: tuple[int, ...] = (0,),
) -> subprocess.CompletedProcess[str]:
    try:
        proc = subprocess.run(
            ["git", *args],
            cwd=cwd,
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as exc:
        raise GitError(f"Failed to execute git {' '.join(args)}: {exc}") from exc

    if proc.returncode not in allowed_returncodes:
        detail = proc.stderr.strip() or proc.stdout.strip() or f"exit code {proc.returncode}"
        raise GitError(f"git {' '.join(args)} failed: {detail}")
    return proc


def ensure_worktree(
    repo_path: Path,
    worktree_path: Path,
    branch_name: str,
    base_ref: str = "HEAD",
) -> Path:
    """Create a git worktree for branch_name if it does not already exist."""
    if worktree_path.exists() and (worktree_path / ".git").exists():
        return worktree_path

    worktree_path.parent.mkdir(parents=True, exist_ok=True)
    ref_check = _run_git(
        repo_path,
        ["show-ref", "--verify", "--quiet", f"refs/heads/{branch_name}"],
        allowed_returncodes=(0, 1),
    )
    if ref_check.returncode == 0:
        _run_git(repo_path, ["worktree", "add", str(worktree_path), branch_name])
    else:
        _run_git(
            repo_path,
            ["worktree", "add", "-b", branch_name, str(worktree_path), base_ref],
        )
    return worktree_path


def rev_parse_head(repo_path: Path) -> str:
    """Return the full commit SHA of HEAD in repo_path."""
    return _run_git(repo_path, ["rev-parse", "HEAD"]).stdout.strip()


def is_dirty(worktree_path: Path) -> bool:
    """Return True if the worktree has modified, staged, or untracked files."""
    proc = _run_git(worktree_path, ["status", "--porcelain"])
    return bool(proc.stdout.strip())


def capture_diff(worktree_path: Path, base_ref: str = "HEAD") -> str:
    """Capture a unified diff of tracked changes and untracked files."""
    tracked = _run_git(worktree_path, ["diff", base_ref]).stdout
    untracked_list = _run_git(
        worktree_path,
        ["ls-files", "--others", "--exclude-standard"],
    ).stdout.splitlines()

    parts: list[str] = [tracked] if tracked else []
    for rel_path in untracked_list:
        if not rel_path:
            continue
        untracked_diff = _run_git(
            worktree_path,
            ["diff", "--no-index", "--", "/dev/null", rel_path],
            allowed_returncodes=(0, 1),
        ).stdout
        if untracked_diff:
            parts.append(untracked_diff)
    return "".join(parts)


def commit_stage(worktree_path: Path, message: str) -> bool:
    """Stage all worktree changes and commit; return False cleanly if worktree is clean."""
    if not is_dirty(worktree_path):
        return False
    _run_git(worktree_path, ["add", "-A"])
    _run_git(worktree_path, ["commit", "-m", message])
    return True
