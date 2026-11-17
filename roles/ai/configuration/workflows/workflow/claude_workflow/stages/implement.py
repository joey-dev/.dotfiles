"""Stage 5: Implement — execute the plan inside an isolated RW worktree."""

from __future__ import annotations

from claude_workflow.config import StageName
from claude_workflow.git_host import commit_stage, ensure_worktree, rev_parse_head
from claude_workflow.sandbox import sandbox_paths
from claude_workflow.stages.base import (
    StageContext,
    StageOutcome,
    StageResult,
    build_stage_sandbox,
    run_headless_with_escalation,
    skill_prompt_prefix,
)
from claude_workflow.state import save_state


class ImplementStage:
    """Apply code changes in a dedicated git worktree and commit on the host."""

    def run(self, ctx: StageContext) -> StageResult:
        """Execute Stage 5 (Implement) and commit host-side changes."""
        branch_name = ctx.state.branch_name or ctx.ticket_id.lower()
        worktree_path = ctx.state.worktree_path or (ctx.config.worktree_base / ctx.ticket_id)
        base_commit = ctx.state.base_commit or rev_parse_head(ctx.config.repo_path)

        ensure_worktree(ctx.config.repo_path, worktree_path, branch_name, base_ref=base_commit)
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
        prompt = skill_prompt_prefix(ctx, StageName.IMPLEMENT, paths) + (
            f"Implement the plan in {paths.notes_dir / '04-plan.md'} inside {paths.repo_dir}. "
            f"Write a brief summary of changes to {paths.notes_dir / '05-implement.md'}. "
            f"If you hit a genuine unknown, write {paths.notes_dir / 'blocked-questions.md'} "
            f"and stop instead of guessing."
        )
        result = run_headless_with_escalation(
            ctx, StageName.IMPLEMENT, sandbox, prompt, summary_md_host
        )
        if result.outcome is StageOutcome.DONE:
            commit_stage(worktree_path, f"{ctx.ticket_id}: implement plan")
        return result
