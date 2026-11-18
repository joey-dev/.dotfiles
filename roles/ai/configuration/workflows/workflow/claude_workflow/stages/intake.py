"""Stage 1: Intake — fetch Jira ticket details via the repo's Atlassian MCP server."""

from __future__ import annotations

from dataclasses import replace

from claude_workflow.config import StageName
from claude_workflow.sandbox import sandbox_paths
from claude_workflow.stages.base import (
    StageContext,
    StageOutcome,
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
        paths = sandbox_paths(sandbox)
        prompt = (
            f"Fetch Jira ticket {ctx.ticket_id} (summary, description, acceptance criteria, "
            f"comments, and linked issues) using the Atlassian MCP tools. "
            f"Write the structured summary to {paths.notes_dir / '01-ticket.md'}."
        )
        result = run_headless_with_escalation(ctx, StageName.INTAKE, sandbox, prompt, artifact)
        if result.outcome is StageOutcome.FAILED:
            hint = (
                " Check that the repo's .mcp.json has the Atlassian server, that it is "
                "logged in on the host (~/.mcp-auth; run `claude` in the repo, then /mcp), "
                "and that stages.intake.allowed_tools matches its tool names."
            )
            return replace(result, message=result.message + hint)
        return result
