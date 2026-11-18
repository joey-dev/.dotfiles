"""Ticket keys are normalized to upper case."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from claude_workflow.config import STAGE_ORDER, default_config
from claude_workflow.pipeline import run_pipeline
from claude_workflow.stages.base import StageContext, StageOutcome, StageResult


class _Done:
    def run(self, ctx: StageContext) -> StageResult:
        return StageResult(StageOutcome.DONE, None, "")


def test_lowercase_ticket_uses_uppercase_state_dir(tmp_path: Path) -> None:
    config = replace(default_config(), state_base=tmp_path)
    runners = {stage: _Done() for stage in STAGE_ORDER}

    assert run_pipeline("proj-1", config, auto=True, stage_runners=runners) == 0

    assert (tmp_path / "PROJ-1").is_dir()
    assert not (tmp_path / "proj-1").exists()
