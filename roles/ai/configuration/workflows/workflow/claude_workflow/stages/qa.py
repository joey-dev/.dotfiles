"""Stage 3: Interactive Q&A — batched clarification with the human."""

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


class QaStage:
    """Run an interactive Claude session to resolve open questions."""

    def run(self, ctx: StageContext) -> StageResult:
        """Execute Stage 3 (Q&A), resuming an interrupted session if one exists."""
        artifact = ctx.state_dir / "03-qa.md"
        existing_sid = ctx.state.session_ids.get(StageName.QA.value)
        resume = existing_sid is not None
        session_id = existing_sid if existing_sid is not None else str(uuid.uuid4())

        if not resume:
            ctx.state.session_ids[StageName.QA.value] = session_id
            save_state(ctx.state_dir, ctx.state)

        sandbox = build_stage_sandbox(
            ctx,
            StageName.QA,
            repo_dir=ctx.config.repo_path,
            kb_dir=ctx.config.kb_path,
            workdir=ctx.config.repo_path,
        )
        prompt = (
            f"Read {ctx.state_dir / '01-ticket.md'} and {ctx.state_dir / '02-findings.md'}. "
            f"Ask batched clarifying questions and record all Q&A incrementally to {artifact}."
        )
        rc = run_claude_interactive(
            ctx.config.stages[StageName.QA],
            sandbox,
            prompt,
            session_id=session_id,
            resume=resume,
        )
        if rc != 0:
            return StageResult(
                outcome=StageOutcome.FAILED,
                artifact_path=None,
                message=f"qa interactive session exited with code {rc}",
            )
        return StageResult(
            outcome=StageOutcome.DONE,
            artifact_path=artifact,
            message="qa completed",
        )
