"""The ticket worktree is created at Explore and used by every repo stage."""

from __future__ import annotations

import subprocess
from dataclasses import replace
from pathlib import Path
from typing import Any
from unittest.mock import patch

from claude_workflow.claude_runner import ClaudeResult
from claude_workflow.config import StageName, WorkflowConfig, default_config
from claude_workflow.deps import SharedDependency
from claude_workflow.stages.base import StageContext, build_stage_sandbox, ensure_ticket_worktree
from claude_workflow.stages.explore import ExploreStage
from claude_workflow.state import TicketState


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=True, text=True
    ).stdout.strip()


def _init_repo(repo: Path) -> None:
    repo.mkdir(parents=True)
    _git(repo, "init")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test")
    (repo / "README.md").write_text("hello\n")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "-m", "init")


def _config(tmp_path: Path) -> WorkflowConfig:
    repo = tmp_path / "repo"
    _init_repo(repo)
    state_base = tmp_path / "state"
    return replace(
        default_config(),
        repo_path=repo,
        state_base=state_base,
        worktree_base=state_base / "worktrees",
        kb_path=tmp_path / "no-kb",
        skills_base=tmp_path / "no-skills",
    )


def _ctx(config: WorkflowConfig) -> StageContext:
    state_dir = config.state_base / "PROJ-1"
    state_dir.mkdir(parents=True, exist_ok=True)
    return StageContext("PROJ-1", config, TicketState("PROJ-1"), state_dir)


def test_explore_mounts_ticket_worktree_not_main_checkout(tmp_path: Path) -> None:
    config = _config(tmp_path)
    ctx = _ctx(config)
    seen: list[Any] = []

    def fake_run(stage: Any, sandbox: Any, prompt: str, **_: Any) -> ClaudeResult:
        seen.append(sandbox)
        (ctx.state_dir / "02-findings.md").write_text("findings")
        return ClaudeResult(0, "", "", None)

    with patch("claude_workflow.stages.base.run_claude_headless", side_effect=fake_run):
        ExploreStage().run(ctx)

    assert seen[0].repo_dir == config.worktree_base / "PROJ-1"
    assert ctx.state.worktree_path == config.worktree_base / "PROJ-1"


def test_worktree_base_is_fixed_after_first_creation(tmp_path: Path) -> None:
    config = _config(tmp_path)
    ctx = _ctx(config)
    first_head = _git(config.repo_path, "rev-parse", "HEAD")
    ensure_ticket_worktree(ctx)

    (config.repo_path / "new.txt").write_text("x")
    _git(config.repo_path, "add", "new.txt")
    _git(config.repo_path, "commit", "-m", "moved on")
    ensure_ticket_worktree(ctx)

    assert ctx.state.base_commit == first_head


def test_dirty_main_checkout_prints_warning(tmp_path: Path, capsys: Any) -> None:
    config = _config(tmp_path)
    (config.repo_path / "README.md").write_text("changed\n")

    ensure_ticket_worktree(_ctx(config))

    assert "uncommitted changes" in capsys.readouterr().out


def test_repo_stages_mount_shared_dependencies(tmp_path: Path) -> None:
    config = _config(tmp_path)
    (config.repo_path / "vendor").mkdir()
    config = replace(
        config, shared_dependencies=(SharedDependency("vendor", "composer.lock"),)
    )
    ctx = _ctx(config)
    worktree = ensure_ticket_worktree(ctx)

    spec = build_stage_sandbox(
        ctx, StageName.EXPLORE, repo_dir=worktree, kb_dir=None, workdir=worktree
    )

    assert spec.repo_ro_overlays == ((config.repo_path / "vendor", "vendor"),)


def test_retro_gets_all_skills_and_claude_md_read_only(tmp_path: Path, monkeypatch: Any) -> None:
    config = _config(tmp_path)
    host_home = tmp_path / "home"
    (host_home / ".claude").mkdir(parents=True)
    (host_home / ".claude" / "CLAUDE.md").write_text("# me")
    monkeypatch.setattr(Path, "home", lambda: host_home)
    ctx = _ctx(config)

    retro = build_stage_sandbox(
        ctx, StageName.RETRO, repo_dir=None, kb_dir=None, workdir=ctx.state_dir
    )
    explore = build_stage_sandbox(
        ctx, StageName.EXPLORE, repo_dir=None, kb_dir=None, workdir=ctx.state_dir
    )

    claude_md = (host_home / ".claude" / "CLAUDE.md", ".claude/CLAUDE.md")
    assert claude_md in retro.home_ro_mounts
    assert (config.skills_base, "skills") in retro.home_ro_mounts
    assert claude_md in explore.home_ro_mounts
    assert (config.skills_base, "skills") not in explore.home_ro_mounts
