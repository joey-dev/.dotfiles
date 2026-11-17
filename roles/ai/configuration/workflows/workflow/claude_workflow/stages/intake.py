"""Stage 1: Intake — fetch Jira ticket details via Atlassian MCP."""

from __future__ import annotations

from claude_workflow.config import StageName
from claude_workflow.stages.base import (
    StageContext,
    StageResult,
    build_stage_sandbox,
    run_headless_with_escalation,
)


class IntakeStage:
    """Fetch Jira ticket summary, description, comments, and linked issues."""

    def run(self, ctx: StageContext) -> StageResult:
        """Execute Stage 1 (Intake) and write 01-ticket.md."""
        artifact = ctx.state_dir / "01-ticket.md"
        sandbox = build_stage_sandbox(
            ctx,
            StageName.INTAKE,
            repo_dir=None,
            kb_dir=None,
            workdir=ctx.state_dir,
        )
        prompt = (
            f"Fetch Jira ticket {ctx.ticket_id} (summary, description, acceptance criteria, "
            f"comments, and linked issues) using the Atlassian MCP tools. "
            f"Follow the intake skill instructions and write the structured summary to {artifact}."
        )
        return run_headless_with_escalation(ctx, StageName.INTAKE, sandbox, prompt, artifact)
