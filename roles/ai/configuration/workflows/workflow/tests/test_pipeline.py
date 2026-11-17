"""Tests for claude_workflow.pipeline and PlanStage."""

from __future__ import annotations

import builtins
from dataclasses import replace
from pathlib import Path
from typing import Any

import claude_workflow.pipeline as pipeline_mod
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
    monkeypatch.setattr(pipeline_mod, "_notify", lambda *_args: None)

    escalation_runs = 0

    def fake_interactive(*_args: Any, **_kwargs: Any) -> int:
        nonlocal escalation_runs
        escalation_runs += 1
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
    cfg.repo_path.mkdir(parents=True)
    state_dir = cfg.state_base / "PROJ-13"
    state_dir.mkdir(parents=True)

    calls: list[str] = []

    def fake_headless(
        stage: Any,
        sandbox: Any,
        prompt: str,
        session_id: str | None = None,
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

    monkeypatch.setattr(plan_mod, "run_claude_headless", fake_headless)

    ctx = StageContext(
        ticket_id="PROJ-13",
        config=cfg,
        state=TicketState(ticket_id="PROJ-13"),
        state_dir=state_dir,
    )
    res = PlanStage().run(ctx)

    assert res.outcome is StageOutcome.DONE
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
