"""Stage 2: Explore — read-only repository and KB exploration."""

from __future__ import annotations

from claude_workflow.config import StageName
from claude_workflow.sandbox import sandbox_paths
from claude_workflow.stages.base import (
    StageContext,
    StageResult,
    build_stage_sandbox,
    run_headless_with_escalation,
    skill_prompt_prefix,
)


class ExploreStage:
    """Inspect the mono-repo read-only to map relevant files, quirks, and gaps."""

    def run(self, ctx: StageContext) -> StageResult:
        """Execute Stage 2 (Explore) and write 02-findings.md."""
        artifact = ctx.state_dir / "02-findings.md"
        sandbox = build_stage_sandbox(
            ctx,
            StageName.EXPLORE,
            repo_dir=ctx.config.repo_path,
            kb_dir=ctx.config.kb_path,
            workdir=ctx.config.repo_path,
        )
        paths = sandbox_paths(sandbox)
        kb_hint = f" (plus any relevant notes in {paths.kb_dir})" if paths.kb_dir else ""
        prompt = skill_prompt_prefix(ctx, StageName.EXPLORE, paths) + (
            f"Read {paths.notes_dir / '01-ticket.md'} and explore the repository at "
            f"{paths.repo_dir}{kb_hint}. Identify relevant files, legacy quirks, and open "
            f"questions, then write {paths.notes_dir / '02-findings.md'}."
        )
        return run_headless_with_escalation(ctx, StageName.EXPLORE, sandbox, prompt, artifact)
