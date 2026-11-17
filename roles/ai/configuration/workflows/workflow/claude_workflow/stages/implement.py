"""Stage 5: Implement — execute the plan inside an isolated RW worktree."""

from __future__ import annotations

from claude_workflow.config import StageName
from claude_workflow.git_host import commit_stage, ensure_worktree
from claude_workflow.stages.base import (
    StageContext,
    StageOutcome,
    StageResult,
    blocked_questions_path,
    build_stage_sandbox,
    run_headless_with_escalation,
)
from claude_workflow.state import save_state


class ImplementStage:
    """Apply code changes in a dedicated git worktree and commit on the host."""

    def run(self, ctx: StageContext) -> StageResult:
        """Execute Stage 5 (Implement) and commit host-side changes."""
        branch_name = ctx.state.branch_name or ctx.ticket_id.lower()
        worktree_path = ctx.state.worktree_path or (ctx.config.worktree_base / ctx.ticket_id)

        ensure_worktree(ctx.config.repo_path, worktree_path, branch_name)
        if ctx.state.worktree_path != worktree_path or ctx.state.branch_name != branch_name:
            ctx.state.worktree_path = worktree_path
            ctx.state.branch_name = branch_name
            save_state(ctx.state_dir, ctx.state)

        sandbox = build_stage_sandbox(
            ctx,
            StageName.IMPLEMENT,
            repo_dir=worktree_path,
            kb_dir=None,
            workdir=worktree_path,
        )
        summary_md = ctx.state_dir / "05-implement.md"
        prompt = (
            f"Implement the plan in {ctx.state_dir / '04-plan.md'} inside {worktree_path}. "
            f"Write a brief summary of changes to {summary_md}. "
            f"If you hit a genuine unknown, write {blocked_questions_path(ctx.state_dir)} "
            f"and stop instead of guessing."
        )
        result = run_headless_with_escalation(
            ctx, StageName.IMPLEMENT, sandbox, prompt, summary_md
        )
        if result.outcome is StageOutcome.DONE:
            commit_stage(worktree_path, f"{ctx.ticket_id}: implement plan")
        return result
