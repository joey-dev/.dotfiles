"""Stage 5: Implement — execute the plan inside an isolated RW worktree."""

from __future__ import annotations

from pathlib import Path

from claude_workflow.catalogue import command_catalogue, verify_summary
from claude_workflow.config import StageName, WorkflowConfig
from claude_workflow.sandbox import sandbox_paths
from claude_workflow.stages.base import (
    StageContext,
    StageResult,
    build_stage_sandbox,
    ensure_ticket_worktree,
    run_headless_with_escalation,
)
from claude_workflow.tests_file import TESTS_FILE, TESTS_LINE_FORMAT


def _test_first_instruction(tests_file: Path, config: WorkflowConfig) -> str:
    """Ask for red-green work driven by tests.txt, and say what Verify runs."""
    text = (
        "Work test-first: for each plan step, write the test, run it and see it fail, "
        "then write the code until it passes. "
        f"Each line of {tests_file} is '{TESTS_LINE_FORMAT}' (commands below). "
        "Run the 'sandbox' commands yourself with the shown line; 'host' and 'container' "
        "commands run only in Verify. "
        f"If you add or rename a test, update {tests_file}. "
    )
    summary = verify_summary(config.verify)
    if summary:
        text += summary + "You may run the sandbox ones yourself on the files you changed. "
    catalogue = command_catalogue(config.commands, run_lines=True)
    return text + ("\n\n" + catalogue + "\n" if catalogue else "")


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
            f"Write a brief summary of changes to {paths.notes_dir / '05-implement.md'}. "
            f"If you hit a genuine unknown, write {paths.notes_dir / 'blocked-questions.md'} "
            f"and stop instead of guessing. "
            f"{_test_first_instruction(paths.notes_dir / TESTS_FILE, ctx.config)}"
        )
        return run_headless_with_escalation(
            ctx, StageName.IMPLEMENT, sandbox, prompt, summary_md_host
        )
