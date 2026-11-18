"""Tests for claude_workflow.pipeline and PlanStage."""

from __future__ import annotations

import builtins
import subprocess
from dataclasses import replace
from pathlib import Path
from typing import Any

import claude_workflow.pipeline as pipeline_mod
import claude_workflow.stages.base as base_mod
import claude_workflow.stages.plan as plan_mod
from claude_workflow.claude_runner import ClaudeResult
from claude_workflow.config import STAGE_ORDER, StageName, WorkflowConfig, default_config
from claude_workflow.pipeline import run_pipeline
from claude_workflow.stages.base import (
    StageContext,
    StageOutcome,
    StageProtocol,
    StageResult,
    blocked_questions_path,
)
from claude_workflow.stages.plan import PlanStage
from claude_workflow.state import TicketState, load_state, save_state


def _test_config(tmp_path: Path) -> WorkflowConfig:
    base = default_config()
    return replace(
        base,
        repo_path=tmp_path / "repo",
        worktree_base=tmp_path / "worktrees",
        state_base=tmp_path / "state",
        kb_path=tmp_path / "kb",
        skills_base=tmp_path / "skills",
    )


def _init_git_repo(repo: Path) -> None:
    """Create a git repo with one commit, so stages can create a ticket worktree."""
    repo.mkdir(parents=True)
    for args in (
        ["init"],
        ["config", "user.email", "test@example.com"],
        ["config", "user.name", "Test"],
        ["commit", "--allow-empty", "-m", "init"],
    ):
        subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


class _FakeStage:
    def __init__(self, calls: list[StageName], name: StageName) -> None:
        self._calls = calls
        self._name = name

    def run(self, ctx: StageContext) -> StageResult:
        self._calls.append(self._name)
        return StageResult(
            outcome=StageOutcome.DONE,
            artifact_path=ctx.state_dir / f"{self._name.value}.md",
            message="ok",
        )


def test_pipeline_runs_all_stages_and_persists_state(tmp_path: Path) -> None:
    cfg = _test_config(tmp_path)
    calls: list[StageName] = []
    runners: dict[StageName, StageProtocol] = {
        stage: _FakeStage(calls, stage) for stage in STAGE_ORDER
    }

    rc = run_pipeline("PROJ-10", cfg, auto=True, stage_runners=runners)

    assert rc == 0
    assert calls == list(STAGE_ORDER)
    loaded = load_state(cfg.state_base / "PROJ-10", "PROJ-10")
    assert loaded.completed_stages == list(STAGE_ORDER)
    assert loaded.current_stage is None


def test_pipeline_resumes_from_interrupted_stage(tmp_path: Path) -> None:
    cfg = _test_config(tmp_path)
    state_dir = cfg.state_base / "PROJ-11"
    save_state(
        state_dir,
        TicketState(
            ticket_id="PROJ-11",
            current_stage=StageName.PLAN,
            completed_stages=[StageName.INTAKE, StageName.EXPLORE, StageName.QA],
        ),
    )

    calls: list[StageName] = []
    runners: dict[StageName, StageProtocol] = {
        stage: _FakeStage(calls, stage) for stage in STAGE_ORDER
    }

    rc = run_pipeline("PROJ-11", cfg, auto=True, stage_runners=runners)

    assert rc == 0
    assert calls == [
        StageName.PLAN,
        StageName.IMPLEMENT,
        StageName.VERIFY,
        StageName.REVIEW,
        StageName.RETRO,
    ]


def test_pipeline_handles_blocked_questions_escalation_and_caps_retries(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    cfg = replace(_test_config(tmp_path), max_escalations=2)
    _init_git_repo(cfg.repo_path)
    monkeypatch.setattr(pipeline_mod, "_notify", lambda *_args: None)

    escalation_runs = 0

    def fake_interactive(_stage: Any, sandbox: Any, *_args: Any, **_kwargs: Any) -> int:
        nonlocal escalation_runs
        escalation_runs += 1
        with (sandbox.state_dir / "03-qa.md").open("a", encoding="utf-8") as answers:
            answers.write("A confirmed answer.\n")
        return 0

    monkeypatch.setattr(pipeline_mod, "run_claude_interactive", fake_interactive)

    class _AlwaysBlockedStage:
        def run(self, ctx: StageContext) -> StageResult:
            bq = blocked_questions_path(ctx.state_dir)
            bq.write_text("Need clarification?\n", encoding="utf-8")
            return StageResult(
                outcome=StageOutcome.BLOCKED_QUESTIONS,
                artifact_path=bq,
                message="blocked",
            )

    runners: dict[StageName, StageProtocol] = {
        stage: _FakeStage([], stage) for stage in STAGE_ORDER
    }
    runners[StageName.PLAN] = _AlwaysBlockedStage()

    rc = run_pipeline(
        "PROJ-12",
        cfg,
        from_stage=StageName.PLAN,
        auto=True,
        stage_runners=runners,
    )

    assert rc == 1
    assert escalation_runs == 2


def test_plan_stage_caps_review_loop_at_max_plan_reviews(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    cfg = replace(_test_config(tmp_path), max_plan_reviews=2)
    _init_git_repo(cfg.repo_path)
    state_dir = cfg.state_base / "PROJ-13"
    state_dir.mkdir(parents=True)

    calls: list[str] = []

    def fake_headless(
        stage: Any,
        sandbox: Any,
        prompt: str,
        session_id: str | None = None,
        **_: Any,
    ) -> ClaudeResult:
        calls.append(prompt)
        if "Review " in prompt:
            (state_dir / "04-plan-review.md").write_text(
                "CHANGES_REQUESTED\n- Fix step 2\n",
                encoding="utf-8",
            )
        else:
            (state_dir / "04-plan.md").write_text("# Plan\n", encoding="utf-8")
        return ClaudeResult(returncode=0, stdout="", stderr="", session_id=session_id)

    monkeypatch.setattr(base_mod, "run_claude_headless", fake_headless)
    monkeypatch.setattr(plan_mod, "run_claude_headless", fake_headless)

    ctx = StageContext(
        ticket_id="PROJ-13",
        config=cfg,
        state=TicketState(ticket_id="PROJ-13"),
        state_dir=state_dir,
    )
    res = PlanStage().run(ctx)

    assert res.outcome is StageOutcome.FAILED
    review_calls = [c for c in calls if "Review " in c]
    assert len(review_calls) == 2


def test_step_gate_allows_retry_continue_and_abort(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    cfg = _test_config(tmp_path)
    calls: list[StageName] = []
    runners: dict[StageName, StageProtocol] = {
        stage: _FakeStage(calls, stage) for stage in STAGE_ORDER
    }

    answers = iter(["r", "c", "a"])
    monkeypatch.setattr(builtins, "input", lambda _prompt: next(answers))

    rc = run_pipeline("PROJ-14", cfg, auto=False, stage_runners=runners)

    assert rc == 1
    assert calls == [StageName.INTAKE, StageName.INTAKE, StageName.EXPLORE]


def test_plan_review_blocker_returns_blocked(tmp_path: Path, monkeypatch: Any) -> None:
    cfg = _test_config(tmp_path)
    _init_git_repo(cfg.repo_path)
    state_dir = cfg.state_base / "PROJ-14"
    state_dir.mkdir(parents=True)

    def fake_headless(stage: Any, sandbox: Any, prompt: str, **_: Any) -> ClaudeResult:
        if "Review " in prompt:
            blocked_questions_path(state_dir).write_text("Which API version?\n")
            (state_dir / "04-plan-review.md").write_text("APPROVED\n")
        else:
            (state_dir / "04-plan.md").write_text("# Plan\n")
        return ClaudeResult(0, "", "", None)

    monkeypatch.setattr(base_mod, "run_claude_headless", fake_headless)
    monkeypatch.setattr(plan_mod, "run_claude_headless", fake_headless)
    ctx = StageContext("PROJ-14", cfg, TicketState("PROJ-14"), state_dir)

    assert PlanStage().run(ctx).outcome is StageOutcome.BLOCKED_QUESTIONS


def test_empty_blocker_is_removed_and_stage_runs(tmp_path: Path) -> None:
    cfg = _test_config(tmp_path)
    state_dir = cfg.state_base / "PROJ-15"
    state_dir.mkdir(parents=True)
    blocked_questions_path(state_dir).write_text("  \n")
    calls: list[StageName] = []
    runners: dict[StageName, StageProtocol] = {
        stage: _FakeStage(calls, stage) for stage in STAGE_ORDER
    }
    save_state(state_dir, TicketState("PROJ-15", completed_stages=list(STAGE_ORDER[:3])))

    rc = run_pipeline("PROJ-15", cfg, auto=True, stage_runners=runners)

    assert rc == 0
    assert StageName.PLAN in calls
    assert not blocked_questions_path(state_dir).exists()


def test_plan_accepts_markdown_approved_verdict(tmp_path: Path, monkeypatch: Any) -> None:
    cfg = _test_config(tmp_path)
    _init_git_repo(cfg.repo_path)
    state_dir = cfg.state_base / "PROJ-16"
    state_dir.mkdir(parents=True)

    def fake_headless(stage: Any, sandbox: Any, prompt: str, **_: Any) -> ClaudeResult:
        if "Review " in prompt:
            (state_dir / "04-plan-review.md").write_text("# **APPROVED**\n\nLooks fine.\n")
        else:
            (state_dir / "04-plan.md").write_text("# Plan\n")
        return ClaudeResult(0, "", "", None)

    monkeypatch.setattr(base_mod, "run_claude_headless", fake_headless)
    monkeypatch.setattr(plan_mod, "run_claude_headless", fake_headless)
    ctx = StageContext("PROJ-16", cfg, TicketState("PROJ-16"), state_dir)

    assert PlanStage().run(ctx).outcome is StageOutcome.DONE


def test_plan_draft_prompt_asks_for_test_first_steps(tmp_path: Path, monkeypatch: Any) -> None:
    cfg = _test_config(tmp_path)
    _init_git_repo(cfg.repo_path)
    state_dir = cfg.state_base / "PROJ-17"
    state_dir.mkdir(parents=True)
    prompts: list[str] = []

    def fake_headless(stage: Any, sandbox: Any, prompt: str, **_: Any) -> ClaudeResult:
        prompts.append(prompt)
        return ClaudeResult(1, "", "stop", None)

    monkeypatch.setattr(base_mod, "run_claude_headless", fake_headless)
    PlanStage().run(StageContext("PROJ-17", cfg, TicketState("PROJ-17"), state_dir))

    assert "test-first" in prompts[0]
