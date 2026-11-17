"""Tests for claude_workflow.sandbox."""

from __future__ import annotations

from pathlib import Path

from claude_workflow.config import RepoAccess
from claude_workflow.sandbox import SandboxSpec, build_bwrap_command


def _has_slice(args: list[str], *items: str) -> bool:
    n = len(items)
    return any(args[i : i + n] == list(items) for i in range(len(args) - n + 1))


def test_bwrap_ro_repo_and_unshare_net(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    state_dir = tmp_path / "state"
    state_dir.mkdir()

    spec = SandboxSpec(
        repo_dir=repo,
        repo_access=RepoAccess.RO,
        state_dir=state_dir,
        skills_dirs=(),
        kb_dir=None,
        allow_network=False,
        workdir=repo,
    )
    cmd = build_bwrap_command(spec, ["claude", "-p", "hello"])

    assert "--unshare-net" in cmd
    assert _has_slice(cmd, "--ro-bind", str(repo), str(repo))
    assert _has_slice(cmd, "--bind", str(state_dir), str(state_dir))
    assert cmd[-4:] == ["--", "claude", "-p", "hello"]


def test_bwrap_hides_git_directory(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)
    state_dir = tmp_path / "state"
    state_dir.mkdir()

    spec = SandboxSpec(
        repo_dir=repo,
        repo_access=RepoAccess.RO,
        state_dir=state_dir,
        skills_dirs=(),
        kb_dir=None,
        allow_network=True,
        workdir=repo,
    )
    cmd = build_bwrap_command(spec, ["claude"])

    assert "--unshare-net" not in cmd
    assert _has_slice(cmd, "--tmpfs", str(repo / ".git"))


def test_bwrap_hides_git_worktree_file(tmp_path: Path) -> None:
    worktree = tmp_path / "wt"
    worktree.mkdir()
    (worktree / ".git").write_text("gitdir: /some/repo/.git/worktrees/wt\n", encoding="utf-8")
    state_dir = tmp_path / "state"
    state_dir.mkdir()

    spec = SandboxSpec(
        repo_dir=worktree,
        repo_access=RepoAccess.RW,
        state_dir=state_dir,
        skills_dirs=(),
        kb_dir=None,
        allow_network=False,
        workdir=worktree,
    )
    cmd = build_bwrap_command(spec, ["claude"])

    assert _has_slice(cmd, "--bind", str(worktree), str(worktree))
    assert _has_slice(cmd, "--ro-bind", "/dev/null", str(worktree / ".git"))
    assert not _has_slice(cmd, "--tmpfs", str(worktree / ".git"))


def test_bwrap_mounts_only_stage_skills_and_ro_kb(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    kb_dir = tmp_path / "kb"
    kb_dir.mkdir()
    shared_skill = tmp_path / "skills" / "shared"
    explore_skill = tmp_path / "skills" / "explore"
    plan_skill = tmp_path / "skills" / "plan"
    shared_skill.mkdir(parents=True)
    explore_skill.mkdir(parents=True)
    plan_skill.mkdir(parents=True)

    spec = SandboxSpec(
        repo_dir=repo,
        repo_access=RepoAccess.RO,
        state_dir=state_dir,
        skills_dirs=(shared_skill, explore_skill),
        kb_dir=kb_dir,
        allow_network=True,
        workdir=repo,
    )
    cmd = build_bwrap_command(spec, ["claude"])

    assert _has_slice(cmd, "--ro-bind", str(kb_dir), str(kb_dir))
    assert _has_slice(cmd, "--ro-bind", str(shared_skill), str(shared_skill))
    assert _has_slice(cmd, "--ro-bind", str(explore_skill), str(explore_skill))
    assert str(plan_skill) not in cmd
