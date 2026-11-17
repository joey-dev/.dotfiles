"""Stage 8: Human Check & Retro — interactive review and KB/skill diff proposal."""

from __future__ import annotations

import uuid

from claude_workflow.claude_runner import run_claude_interactive
from claude_workflow.config import StageName
from claude_workflow.stages.base import (
    StageContext,
    StageOutcome,
    StageResult,
    build_stage_sandbox,
)
from claude_workflow.state import save_state


class RetroStage:
    """Present verification/review results and propose KB or skill updates."""

    def run(self, ctx: StageContext) -> StageResult:
        """Execute Stage 8 (Retro) interactively."""
        artifact = ctx.state_dir / "08-retro.md"
        existing_sid = ctx.state.session_ids.get(StageName.RETRO.value)
        resume = existing_sid is not None
        session_id = existing_sid if existing_sid is not None else str(uuid.uuid4())

        if not resume:
            ctx.state.session_ids[StageName.RETRO.value] = session_id
            save_state(ctx.state_dir, ctx.state)

        sandbox = build_stage_sandbox(
            ctx,
            StageName.RETRO,
            repo_dir=None,
            kb_dir=ctx.config.kb_path,
            workdir=ctx.state_dir,
        )
        prompt = (
            f"Review {ctx.state_dir / '06-verify.md'} and {ctx.state_dir / '07-review.md'} "
            f"with the user. Capture any human feedback and propose concrete diffs to skills "
            f"or the personal KB in {artifact}."
        )
        rc = run_claude_interactive(
            ctx.config.stages[StageName.RETRO],
            sandbox,
            prompt,
            session_id=session_id,
            resume=resume,
        )
        if rc != 0:
            return StageResult(
                outcome=StageOutcome.FAILED,
                artifact_path=None,
                message=f"retro interactive session exited with code {rc}",
            )
        return StageResult(
            outcome=StageOutcome.DONE,
            artifact_path=artifact,
            message="retro completed",
        )
