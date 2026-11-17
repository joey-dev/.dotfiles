"""Tests for claude_workflow.git_host."""

from __future__ import annotations

import subprocess
from pathlib import Path

from claude_workflow.git_host import (
    capture_diff,
    commit_stage,
    ensure_worktree,
    is_dirty,
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
