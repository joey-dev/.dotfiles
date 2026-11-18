"""Stage 5: Implement — execute the plan inside an isolated RW worktree."""

from __future__ import annotations

from claude_workflow.config import StageName
from claude_workflow.sandbox import sandbox_paths
from claude_workflow.stages.base import (
    StageContext,
    StageResult,
    build_stage_sandbox,
    ensure_ticket_worktree,
    run_headless_with_escalation,
)


def _test_first_instruction(verify_commands: tuple[str, ...]) -> str:
    """Ask for red-green work, and say which commands run the checks."""
    text = (
        "Work test-first: for each plan step, write the test, run it and see it fail, "
        "then write the code until it passes. "
    )
    if verify_commands:
        text += (
            f"Check commands: {'; '.join(verify_commands)}. "
            "You may run a single test file with the same tools. "
        )
    return text


class ImplementStage:
    """Apply code changes in a dedicated git worktree."""

    def run(self, ctx: StageContext) -> StageResult:
        """Execute Stage 5 (Implement)."""
        worktree_path = ensure_ticket_worktree(ctx)
        sandbox = build_stage_sandbox(
            ctx,
            StageName.IMPLEMENT,
            repo_dir=worktree_path,
            kb_dir=None,
            workdir=worktree_path,
        )
        paths = sandbox_paths(sandbox)
        summary_md_host = ctx.state_dir / "05-implement.md"
        fix_request = ""
        if ctx.state.fix_feedback:
            fix_request = (
                f"Fix the problems listed in {paths.notes_dir / ctx.state.fix_feedback}. "
            )
        prompt = (
            f"Implement the plan in {paths.notes_dir / '04-plan.md'} inside {paths.repo_dir}. "
            f"Read {paths.notes_dir / '03-qa.md'}, including any escalation answers. "
            f"{fix_request}"
            f"{_test_first_instruction(ctx.config.verify_commands)}"
            f"Write a brief summary of changes to {paths.notes_dir / '05-implement.md'}. "
            f"If you hit a genuine unknown, write {paths.notes_dir / 'blocked-questions.md'} "
            f"and stop instead of guessing."
        )
        return run_headless_with_escalation(
            ctx, StageName.IMPLEMENT, sandbox, prompt, summary_md_host
        )
