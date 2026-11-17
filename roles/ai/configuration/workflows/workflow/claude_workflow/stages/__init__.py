"""Pipeline stage implementations."""

from __future__ import annotations

from claude_workflow.config import StageName
from claude_workflow.stages.base import StageOutcome, StageProtocol, StageResult
from claude_workflow.stages.explore import ExploreStage
from claude_workflow.stages.implement import ImplementStage
from claude_workflow.stages.intake import IntakeStage
from claude_workflow.stages.plan import PlanStage
from claude_workflow.stages.qa import QaStage
from claude_workflow.stages.retro import RetroStage
from claude_workflow.stages.review import ReviewStage
from claude_workflow.stages.verify import VerifyStage

STAGE_REGISTRY: dict[StageName, StageProtocol] = {
    StageName.INTAKE: IntakeStage(),
    StageName.EXPLORE: ExploreStage(),
    StageName.QA: QaStage(),
    StageName.PLAN: PlanStage(),
    StageName.IMPLEMENT: ImplementStage(),
    StageName.VERIFY: VerifyStage(),
    StageName.REVIEW: ReviewStage(),
    StageName.RETRO: RetroStage(),
}

__all__ = [
    "STAGE_REGISTRY",
    "StageOutcome",
    "StageProtocol",
    "StageResult",
]
