"""Stage 7: Code Review — two focused read-only lenses over diff.patch."""

from __future__ import annotations

from claude_workflow.claude_runner import run_claude_headless
from claude_workflow.config import StageName
from claude_workflow.git_host import capture_diff
from claude_workflow.sandbox import sandbox_paths
from claude_workflow.stages.base import (
    StageContext,
    StageOutcome,
    StageResult,
    build_stage_sandbox,
    read_artifact,
    skill_prompt_prefix,
)

_LENSES: tuple[tuple[str, str], ...] = (
    (
        "correctness",
        "Review diff.patch strictly for logic bugs, edge cases, error handling, "
        "missing tests, and regressions against 01-ticket.md and 04-plan.md.",
    ),
    (
        "conventions",
        "Review diff.patch strictly for codebase conventions, readability, "
        "maintainability, and unnecessary complexity.",
    ),
)


class ReviewStage:
    """Run Correctness and Conventions review lenses and combine into 07-review.md."""

    def run(self, ctx: StageContext) -> StageResult:
        """Capture diff.patch from base_commit and run 2 read-only review passes."""
        worktree = ctx.state.worktree_path or ctx.config.repo_path
        base_ref = ctx.state.base_commit or "HEAD"
        diff_patch_host = ctx.state_dir / "diff.patch"
        diff_text = capture_diff(worktree, base_ref=base_ref)
        diff_patch_host.write_text(diff_text, encoding="utf-8")

        sandbox = build_stage_sandbox(
            ctx,
            StageName.REVIEW,
            repo_dir=worktree,
            kb_dir=ctx.config.kb_path,
            workdir=worktree,
        )
        paths = sandbox_paths(sandbox)
        stage_cfg = ctx.config.stages[StageName.REVIEW]
        combined_sections: list[str] = ["# Automated Code Review\n"]
        prefix = skill_prompt_prefix(ctx, StageName.REVIEW, paths)

        for lens_name, focus in _LENSES:
            lens_host = ctx.state_dir / f"07-review-{lens_name}.md"
            lens_sandbox = paths.notes_dir / f"07-review-{lens_name}.md"
            prompt = prefix + (
                f"Read {paths.notes_dir / 'diff.patch'}, "
                f"{paths.notes_dir / '01-ticket.md'}, and "
                f"{paths.notes_dir / '04-plan.md'}. Focus: {focus} "
                f"Write findings to {lens_sandbox}."
            )
            res = run_claude_headless(stage_cfg, sandbox, prompt)
            if res.returncode != 0:
                return StageResult(
                    outcome=StageOutcome.FAILED,
                    artifact_path=None,
                    message=f"review ({lens_name}) failed: {res.stderr.strip()}",
                )
            body = read_artifact(lens_host) or res.stdout
            combined_sections.append(f"## Lens: {lens_name.title()}\n\n{body.strip()}\n")

        artifact = ctx.state_dir / "07-review.md"
        artifact.write_text("\n".join(combined_sections), encoding="utf-8")
        return StageResult(
            outcome=StageOutcome.DONE,
            artifact_path=artifact,
            message="review completed",
        )
