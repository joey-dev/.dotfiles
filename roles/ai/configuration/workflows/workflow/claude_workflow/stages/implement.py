"""Stage 5: Implement — execute the plan inside an isolated RW worktree."""

from __future__ import annotations

from claude_workflow.config import StageName
from claude_workflow.git_host import ensure_worktree, is_dirty, rev_parse_head
from claude_workflow.sandbox import sandbox_paths
from claude_workflow.stages.base import (
    StageContext,
    StageResult,
    artifact_stamp,
    build_stage_sandbox,
    run_headless_with_escalation,
    skill_prompt_prefix,
)
from claude_workflow.state import save_state


class ImplementStage:
    """Apply code changes in a dedicated git worktree."""

    def run(self, ctx: StageContext) -> StageResult:
        """Execute Stage 5 (Implement)."""
        branch_name = ctx.state.branch_name or ctx.ticket_id.lower()
        worktree_path = ctx.state.worktree_path or (ctx.config.worktree_base / ctx.ticket_id)
        base_commit = ctx.state.base_commit or rev_parse_head(ctx.config.repo_path)

        ensure_worktree(ctx.config.repo_path, worktree_path, branch_name, base_ref=base_commit)
        if ctx.state.worktree_path is None and is_dirty(worktree_path):
            raise RuntimeError(f"Existing worktree has unowned changes: {worktree_path}")
        if (
            ctx.state.worktree_path != worktree_path
            or ctx.state.branch_name != branch_name
            or ctx.state.base_commit != base_commit
        ):
            ctx.state.worktree_path = worktree_path
            ctx.state.branch_name = branch_name
            ctx.state.base_commit = base_commit
            save_state(ctx.state_dir, ctx.state)

        sandbox = build_stage_sandbox(
            ctx,
            StageName.IMPLEMENT,
            repo_dir=worktree_path,
            kb_dir=None,
            workdir=worktree_path,
        )
        paths = sandbox_paths(sandbox)
        summary_md_host = ctx.state_dir / "05-implement.md"
        prior_review = ""
        review = ctx.state_dir / "07-review.md"
        if artifact_stamp(review) is not None:
            prior_review = (
                f"Read the previous review in {paths.notes_dir / review.name} and address "
                "findings that still apply to the current plan and worktree. "
            )
        prompt = skill_prompt_prefix(ctx, StageName.IMPLEMENT, paths) + (
            f"Implement the plan in {paths.notes_dir / '04-plan.md'} inside {paths.repo_dir}. "
            f"Read {paths.notes_dir / '03-qa.md'}, including any escalation answers. "
            f"{prior_review}"
            f"Write a brief summary of changes to {paths.notes_dir / '05-implement.md'}. "
            f"If you hit a genuine unknown, write {paths.notes_dir / 'blocked-questions.md'} "
            f"and stop instead of guessing."
        )
        return run_headless_with_escalation(
            ctx, StageName.IMPLEMENT, sandbox, prompt, summary_md_host
        )
