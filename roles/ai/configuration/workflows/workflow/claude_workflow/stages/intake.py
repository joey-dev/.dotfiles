"""Stage 1: Intake — fetch Jira ticket details via Atlassian MCP."""

from __future__ import annotations

import json
from pathlib import Path

from claude_workflow.config import StageName
from claude_workflow.sandbox import sandbox_paths
from claude_workflow.stages.base import (
    StageContext,
    StageOutcome,
    StageResult,
    build_stage_sandbox,
    run_headless_with_escalation,
    skill_prompt_prefix,
)


class IntakeStage:
    """Fetch Jira ticket summary, description, comments, and linked issues."""

    def run(self, ctx: StageContext) -> StageResult:
        """Execute Stage 1 (Intake) and write 01-ticket.md."""
        artifact = ctx.state_dir / "01-ticket.md"
        if ctx.config.stages[StageName.INTAKE].mcp_config is None:
            inherited = ctx.state_dir / "home" / ".claude.json"
            if not inherited.is_file():
                inherited = Path.home() / ".claude.json"
            settings = (
                json.loads(inherited.read_text(encoding="utf-8")) if inherited.is_file() else {}
            )
            servers = settings.get("mcpServers", {}) if isinstance(settings, dict) else {}
            if not isinstance(servers, dict) or "atlassian" not in servers:
                return StageResult(
                    StageOutcome.FAILED,
                    None,
                    "Configure an atlassian MCP server or set stages.intake.mcp_config.",
                )
        sandbox = build_stage_sandbox(
            ctx,
            StageName.INTAKE,
            repo_dir=None,
            kb_dir=None,
            workdir=ctx.state_dir,
        )
        paths = sandbox_paths(sandbox)
        prompt = skill_prompt_prefix(ctx, StageName.INTAKE, paths) + (
            f"Fetch Jira ticket {ctx.ticket_id} (summary, description, acceptance criteria, "
            f"comments, and linked issues) using the Atlassian MCP tools. "
            f"Write the structured summary to {paths.notes_dir / '01-ticket.md'}."
        )
        return run_headless_with_escalation(ctx, StageName.INTAKE, sandbox, prompt, artifact)
