"""Host-side git worktree, diff, and commit helpers (never push/fetch/pull)."""

from __future__ import annotations

import re
import subprocess
from collections.abc import Sequence
from hashlib import sha256
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
        source = _run_git(repo_path, ["rev-parse", "--path-format=absolute", "--git-common-dir"])
        target = _run_git(worktree_path, ["rev-parse", "--path-format=absolute", "--git-common-dir"])
        if Path(source.stdout.strip()).resolve() != Path(target.stdout.strip()).resolve():
            raise GitError(f"Worktree belongs to another repository: {worktree_path}")
        branch = _run_git(worktree_path, ["symbolic-ref", "--short", "HEAD"]).stdout.strip()
        if branch != branch_name:
            raise GitError(f"Expected branch {branch_name} in {worktree_path}, found {branch}")
        _run_git(worktree_path, ["merge-base", "--is-ancestor", base_ref, "HEAD"])
        return worktree_path

    worktree_path.parent.mkdir(parents=True, exist_ok=True)
    ref_check = _run_git(
        repo_path,
        ["show-ref", "--verify", "--quiet", f"refs/heads/{branch_name}"],
        allowed_returncodes=(0, 1),
    )
    if ref_check.returncode == 0:
        _run_git(repo_path, ["merge-base", "--is-ancestor", base_ref, branch_name])
        _run_git(repo_path, ["worktree", "add", str(worktree_path), branch_name])
    else:
        _run_git(
            repo_path,
            ["worktree", "add", "-b", branch_name, str(worktree_path), base_ref],
        )
    return worktree_path


def repo_root(path: Path) -> Path:
    """Return the top-level folder of the git repository that contains path."""
    return Path(_run_git(path, ["rev-parse", "--show-toplevel"]).stdout.strip()).resolve()


def rev_parse_head(repo_path: Path) -> str:
    """Return the full commit SHA of HEAD in repo_path."""
    return _run_git(repo_path, ["rev-parse", "HEAD"]).stdout.strip()


def is_dirty(worktree_path: Path) -> bool:
    """Return True if the worktree has modified, staged, or untracked files."""
    proc = _run_git(worktree_path, ["status", "--porcelain"])
    return bool(proc.stdout.strip())


def capture_diff(worktree_path: Path, base_ref: str = "HEAD") -> str:
    """Capture a unified diff of tracked changes and untracked files."""
    options = ("--no-color", "--no-ext-diff", "--no-textconv", "--binary", "--full-index")
    tracked = _run_git(worktree_path, ["diff", *options, "--no-renames", base_ref, "--"]).stdout
    untracked_list = _run_git(
        worktree_path,
        ["ls-files", "-z", "--others", "--exclude-standard"],
    ).stdout.split("\0")

    parts: list[str] = [tracked] if tracked else []
    for rel_path in untracked_list:
        if not rel_path:
            continue
        untracked_diff = _run_git(
            worktree_path,
            ["diff", "--no-index", *options, "--", "/dev/null", rel_path],
            allowed_returncodes=(0, 1),
        ).stdout
        if untracked_diff:
            parts.append(untracked_diff)
    return "".join(parts)


def _split_z(output: str) -> list[str]:
    return [item for item in output.split("\0") if item]


def _paths_vs_base(worktree_path: Path, base_ref: str, *, include_deleted: bool) -> list[str]:
    diff_args = ["diff", "-z", "--name-only", "--no-renames"]
    if not include_deleted:
        diff_args.append("--diff-filter=d")
    tracked = _split_z(_run_git(worktree_path, [*diff_args, base_ref, "--"]).stdout)
    untracked = _split_z(
        _run_git(worktree_path, ["ls-files", "-z", "--others", "--exclude-standard"]).stdout
    )
    return sorted(set(tracked) | set(untracked))


def changed_paths(worktree_path: Path, base_ref: str) -> list[str]:
    """Return sorted repo-relative paths changed vs base_ref (tracked + untracked), no deletions."""
    return _paths_vs_base(worktree_path, base_ref, include_deleted=False)


def touched_paths(worktree_path: Path, base_ref: str) -> list[str]:
    """Like changed_paths, but also includes deleted files (for the Docker guard)."""
    return _paths_vs_base(worktree_path, base_ref, include_deleted=True)


def ignored_paths(worktree_path: Path) -> list[str]:
    """Return gitignored paths (ignored directories are listed once, without trailing slash)."""
    proc = _run_git(
        worktree_path,
        ["ls-files", "-z", "--others", "--ignored", "--exclude-standard", "--directory"],
    )
    return sorted(item.rstrip("/") for item in _split_z(proc.stdout))


def diff_digest(diff: str) -> str:
    """Fingerprint patch content independently of tracked/untracked listing order."""
    sections = re.split(r"(?m)(?=^diff --git )", diff)
    return sha256("".join(sorted(sections)).encode()).hexdigest()


def _sections_by_file(diff: str) -> dict[str, str]:
    sections = re.split(r"(?m)(?=^diff --git )", diff)
    by_file: dict[str, str] = {}
    for section in sections:
        header = section.split("\n", 1)[0]
        if header.startswith("diff --git a/"):
            by_file[header.split(" b/", 1)[0].removeprefix("diff --git a/")] = section
    return by_file


def changed_files(before: str, after: str) -> list[str]:
    """Return the files whose patch differs between two captured diffs, sorted."""
    old, new = _sections_by_file(before), _sections_by_file(after)
    return sorted(path for path in old.keys() | new.keys() if old.get(path) != new.get(path))


def commit_stage(worktree_path: Path, message: str, *, no_verify: bool = False) -> bool:
    """Stage all worktree changes and commit; return False cleanly if worktree is clean.

    no_verify skips the repo's git hooks (they could fail or reformat files).
    """
    if not is_dirty(worktree_path):
        return False
    _run_git(worktree_path, ["add", "-A"])
    extra = ["--no-verify"] if no_verify else []
    _run_git(worktree_path, ["commit", *extra, "-m", message])
    return True
