"""Tests for claude_workflow.state."""

from __future__ import annotations

from pathlib import Path

from claude_workflow.config import StageName
from claude_workflow.state import (
    TicketState,
    load_state,
    next_stage_to_run,
    save_state,
)


def test_save_and_load_state_atomic(tmp_path: Path) -> None:
    state_dir = tmp_path / "PROJ-123"
    original = TicketState(
        ticket_id="PROJ-123",
        current_stage=StageName.PLAN,
        completed_stages=[StageName.INTAKE, StageName.EXPLORE, StageName.QA],
        session_ids={"qa": "uuid-1234"},
        worktree_path=tmp_path / "wt",
        branch_name="proj-123",
        escalation_counts={"plan": 1},
    )

    save_state(state_dir, original)
    assert not (state_dir / "state.json.tmp").exists()
    assert (state_dir / "state.json").is_file()

    loaded = load_state(state_dir, "PROJ-123")
    assert loaded == original


def test_next_stage_resumes_interrupted_current_stage() -> None:
    state = TicketState(
        ticket_id="PROJ-123",
        current_stage=StageName.PLAN,
        completed_stages=[StageName.INTAKE, StageName.EXPLORE, StageName.QA],
    )

    assert next_stage_to_run(state, from_stage=None) is StageName.PLAN


def test_next_stage_with_from_stage_override() -> None:
    state = TicketState(
        ticket_id="PROJ-123",
        current_stage=StageName.IMPLEMENT,
        completed_stages=[
            StageName.INTAKE,
            StageName.EXPLORE,
            StageName.QA,
            StageName.PLAN,
        ],
    )

    assert next_stage_to_run(state, from_stage=StageName.EXPLORE) is StageName.EXPLORE
