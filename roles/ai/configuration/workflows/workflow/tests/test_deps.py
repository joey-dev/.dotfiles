"""Shared dependency folders (vendor/, node_modules/) from the main checkout."""

from __future__ import annotations

from pathlib import Path

import pytest

from claude_workflow.deps import (
    DependencyMismatch,
    SharedDependency,
    resolve_shared_dependencies,
)

VENDOR = (SharedDependency(dir="vendor", lockfile="composer.lock"),)


def _setup(tmp_path: Path, main_lock: str | None, tree_lock: str | None) -> tuple[Path, Path]:
    main, tree = tmp_path / "main", tmp_path / "tree"
    (main / "vendor").mkdir(parents=True)
    (main / "vendor" / "autoload.php").write_text("<?php")
    tree.mkdir()
    if main_lock is not None:
        (main / "composer.lock").write_text(main_lock)
    if tree_lock is not None:
        (tree / "composer.lock").write_text(tree_lock)
    return main, tree


def test_mounts_main_dir_when_lockfiles_match(tmp_path: Path) -> None:
    main, tree = _setup(tmp_path, "v1", "v1")

    assert resolve_shared_dependencies(main, tree, VENDOR) == ((main / "vendor", "vendor"),)


def test_creates_empty_mountpoint_in_worktree(tmp_path: Path) -> None:
    main, tree = _setup(tmp_path, "v1", "v1")

    resolve_shared_dependencies(main, tree, VENDOR)

    assert (tree / "vendor").is_dir()
    assert not any((tree / "vendor").iterdir())


def test_worktree_own_dir_is_used_instead(tmp_path: Path) -> None:
    main, tree = _setup(tmp_path, "v1", "v2")
    (tree / "vendor").mkdir()
    (tree / "vendor" / "autoload.php").write_text("<?php")

    assert resolve_shared_dependencies(main, tree, VENDOR) == ()


def test_lockfile_differs_raises(tmp_path: Path) -> None:
    main, tree = _setup(tmp_path, "v1", "v2")

    with pytest.raises(DependencyMismatch, match="composer.lock"):
        resolve_shared_dependencies(main, tree, VENDOR)


def test_lockfile_missing_on_one_side_is_mismatch(tmp_path: Path) -> None:
    main, tree = _setup(tmp_path, "v1", None)

    with pytest.raises(DependencyMismatch):
        resolve_shared_dependencies(main, tree, VENDOR)


def test_missing_main_dir_is_skipped(tmp_path: Path) -> None:
    main, tree = _setup(tmp_path, "v1", "v1")
    (main / "vendor" / "autoload.php").unlink()
    (main / "vendor").rmdir()

    assert resolve_shared_dependencies(main, tree, VENDOR) == ()


def test_missing_main_dir_is_skipped_even_if_lockfiles_differ(tmp_path: Path) -> None:
    # Nothing to mount, so a lockfile difference does not matter.
    main, tree = _setup(tmp_path, "v1", "v2")
    (main / "vendor" / "autoload.php").unlink()
    (main / "vendor").rmdir()

    assert resolve_shared_dependencies(main, tree, VENDOR) == ()
