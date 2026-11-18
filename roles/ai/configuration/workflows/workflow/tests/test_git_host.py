"""Tests for claude_workflow.git_host."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from claude_workflow.git_host import (
    GitError,
    capture_diff,
    changed_files,
    commit_stage,
    ensure_worktree,
    is_dirty,
    repo_root,
    rev_parse_head,
)


def _init_repo(repo: Path) -> None:
    repo.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    (repo / "README.md").write_text("hello\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "init"],
        cwd=repo,
        check=True,
        capture_output=True,
    )


def test_ensure_worktree_creates_branch_and_is_idempotent(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    wt = tmp_path / "worktrees" / "proj-1"

    first = ensure_worktree(repo, wt, "proj-1")
    second = ensure_worktree(repo, wt, "proj-1")

    assert first == wt
    assert second == wt
    assert (wt / ".git").exists()
    branch = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=wt,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    assert branch == "proj-1"


def test_capture_diff_includes_untracked_and_modified(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    wt = ensure_worktree(repo, tmp_path / "wt", "proj-2")

    (wt / "README.md").write_text("hello world\n", encoding="utf-8")
    (wt / "new_file.txt").write_text("brand new\n", encoding="utf-8")

    diff = capture_diff(wt)
    assert "README.md" in diff
    assert "+hello world" in diff
    assert "new_file.txt" in diff
    assert "+brand new" in diff


def test_commit_stage_returns_false_when_clean_and_true_when_dirty(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    wt = ensure_worktree(repo, tmp_path / "wt", "proj-3")

    assert not is_dirty(wt)
    assert commit_stage(wt, "empty") is False

    (wt / "change.txt").write_text("data\n", encoding="utf-8")
    assert is_dirty(wt)
    assert commit_stage(wt, "add change") is True
    assert not is_dirty(wt)


def test_capture_diff_against_base_commit_includes_committed_changes(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    base_sha = rev_parse_head(repo)
    wt = ensure_worktree(repo, tmp_path / "wt", "proj-4", base_ref=base_sha)

    (wt / "feature.py").write_text("def x() -> int:\n    return 1\n", encoding="utf-8")
    assert commit_stage(wt, "implement feature") is True

    diff = capture_diff(wt, base_ref=base_sha)
    assert "feature.py" in diff
    assert "+def x() -> int:" in diff


def test_repo_root_returns_toplevel_from_subdir(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    (repo / "sub").mkdir()

    assert repo_root(repo / "sub") == repo.resolve()


def test_repo_root_outside_git_raises(tmp_path: Path) -> None:
    with pytest.raises(GitError):
        repo_root(tmp_path)


def test_changed_files_between_diffs() -> None:
    before = "diff --git a/a.php b/a.php\n+one\ndiff --git a/b.php b/b.php\n+two\n"
    after = (
        "diff --git a/a.php b/a.php\n+one\n"
        "diff --git a/b.php b/b.php\n+two formatted\n"
        "diff --git a/coverage.xml b/coverage.xml\n+x\n"
    )

    assert changed_files(before, after) == ["b.php", "coverage.xml"]


def _repo_with_failing_hook(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    _init_repo(repo)
    hook = repo / ".git" / "hooks" / "pre-commit"
    hook.write_text("#!/bin/sh\nexit 1\n")
    hook.chmod(0o755)
    (repo / "new.txt").write_text("x\n")
    return repo


def test_commit_no_verify_skips_failing_hook(tmp_path: Path) -> None:
    repo = _repo_with_failing_hook(tmp_path)

    assert commit_stage(repo, "msg", no_verify=True) is True


def test_commit_runs_hooks_by_default(tmp_path: Path) -> None:
    repo = _repo_with_failing_hook(tmp_path)

    with pytest.raises(GitError):
        commit_stage(repo, "msg")
