"""Stage 2: Explore — read-only repository and KB exploration."""

from __future__ import annotations

from claude_workflow.config import StageName
from claude_workflow.stages.base import (
    StageContext,
    StageResult,
    build_stage_sandbox,
    run_headless_with_escalation,
)


class ExploreStage:
    """Inspect the mono-repo read-only to map relevant files, quirks, and gaps."""

    def run(self, ctx: StageContext) -> StageResult:
        """Execute Stage 2 (Explore) and write 02-findings.md."""
        ticket_md = ctx.state_dir / "01-ticket.md"
        artifact = ctx.state_dir / "02-findings.md"
        sandbox = build_stage_sandbox(
            ctx,
            StageName.EXPLORE,
            repo_dir=ctx.config.repo_path,
            kb_dir=ctx.config.kb_path,
            workdir=ctx.config.repo_path,
        )
        prompt = (
            f"Read {ticket_md} and explore the repository at {ctx.config.repo_path} "
            f"(plus any relevant notes in {ctx.config.kb_path}). "
            f"Identify relevant files, legacy quirks, and open questions, then write {artifact}."
        )
        return run_headless_with_escalation(ctx, StageName.EXPLORE, sandbox, prompt, artifact)
