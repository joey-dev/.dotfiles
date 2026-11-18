"""Share dependency folders (vendor/, node_modules/) from the main checkout.

A fresh worktree has no installed dependencies, and the sandbox has no network
to install them. Instead, the main checkout's folders are mounted read-only into
the worktree, but only when the lockfiles match.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SharedDependency:
    """A dependency folder and the lockfile that decides what is inside it."""

    dir: str
    lockfile: str


class DependencyMismatch(ValueError):
    """The worktree needs different dependencies than the main checkout has."""


def _read_lockfile(path: Path) -> bytes | None:
    return path.read_bytes() if path.is_file() else None


def _has_files(folder: Path) -> bool:
    return folder.is_dir() and any(folder.iterdir())


def resolve_shared_dependencies(
    main_repo: Path,
    worktree: Path,
    deps: tuple[SharedDependency, ...],
) -> tuple[tuple[Path, str], ...]:
    """Return (host folder, repo-relative target) pairs to mount read-only.

    Rules, per dependency, in this order:
    1. The worktree has its own non-empty folder: use it, mount nothing.
    2. The main checkout has no such folder: nothing to mount, skip.
    3. The lockfile differs (missing on one side counts): raise DependencyMismatch.
    4. Otherwise: create an empty mount point in the worktree and mount main's folder.
    """
    mounts: list[tuple[Path, str]] = []
    for dep in deps:
        main_dir = main_repo / dep.dir
        tree_dir = worktree / dep.dir

        if _has_files(tree_dir):
            continue

        if not main_dir.is_dir():
            continue

        main_lock = _read_lockfile(main_repo / dep.lockfile)
        tree_lock = _read_lockfile(worktree / dep.lockfile)
        if main_lock != tree_lock:
            raise DependencyMismatch(
                f"{dep.lockfile} differs from {main_repo}. "
                f"Run the install in {worktree}/ on the host, then rerun."
            )

        # bwrap needs an existing folder to mount on, also for read-only repo mounts.
        tree_dir.mkdir(parents=True, exist_ok=True)
        mounts.append((main_dir, dep.dir))
    return tuple(mounts)
