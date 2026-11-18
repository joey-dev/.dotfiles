"""Stage 4: Plan — draft implementation plan with capped reviewer passes."""

from __future__ import annotations

from claude_workflow.claude_runner import run_claude_headless
from claude_workflow.config import StageName
from claude_workflow.sandbox import sandbox_paths
from claude_workflow.tests_file import TESTS_FILE
from claude_workflow.stages.base import (
    StageContext,
    StageOutcome,
    StageResult,
    artifact_result,
    artifact_stamp,
    blocked_result,
    build_stage_sandbox,
    ensure_ticket_worktree,
    has_blocker,
    parse_verdict,
    read_artifact,
    run_headless_with_escalation,
)


class PlanStage:
    """Draft 04-plan.md and run up to max_plan_reviews adversarial review passes."""

    def run(self, ctx: StageContext) -> StageResult:
        """Execute Stage 4 (Plan) and write 04-plan.md."""
        plan_md_host = ctx.state_dir / "04-plan.md"
        review_md_host = ctx.state_dir / "04-plan-review.md"
        worktree = ensure_ticket_worktree(ctx)
        sandbox = build_stage_sandbox(
            ctx,
            StageName.PLAN,
            repo_dir=worktree,
            kb_dir=ctx.config.kb_path,
            workdir=worktree,
        )
        paths = sandbox_paths(sandbox)
        plan_md = paths.notes_dir / "04-plan.md"
        review_md = paths.notes_dir / "04-plan-review.md"
        blocked_md = paths.notes_dir / "blocked-questions.md"
        tests_md = paths.notes_dir / TESTS_FILE

        draft_prompt = (
            f"Read {paths.notes_dir / '01-ticket.md'}, "
            f"{paths.notes_dir / '02-findings.md'}, and "
            f"{paths.notes_dir / '03-qa.md'}. Write a concrete, step-by-step implementation and "
            f"test plan to {plan_md}. Write the plan test-first: each step names the test to "
            f"write before the code it covers. Also write {tests_md}: one line per test to run, "
            f"'flake: <command>' or 'docker: <test_runner.sh arguments>'. List every test you "
            f"plan to create or edit. If you hit a genuine unknown, write {blocked_md} "
            f"and stop instead of guessing."
        )
        draft_result = run_headless_with_escalation(
            ctx, StageName.PLAN, sandbox, draft_prompt, plan_md_host
        )
        if draft_result.outcome is not StageOutcome.DONE:
            return draft_result

        stage_cfg = ctx.config.stages[StageName.PLAN]
        for pass_idx in range(1, ctx.config.max_plan_reviews + 1):
            review_prompt = (
                f"Review {plan_md} critically (pass {pass_idx}/{ctx.config.max_plan_reviews}) "
                f"against {paths.notes_dir / '01-ticket.md'} and "
                f"{paths.notes_dir / '03-qa.md'}. "
                f"Write your review to {review_md}. Start the file with 'APPROVED' if the plan "
                f"is ready, or 'CHANGES_REQUESTED' followed by concrete fixes. Also check {tests_md}: "
                f"it must list every test the plan creates or edits."
            )
            previous = artifact_stamp(review_md_host)
            rev = run_claude_headless(
                stage_cfg, sandbox, review_prompt, timeout=ctx.config.headless_timeout
            )
            if rev.returncode != 0:
                return StageResult(
                    outcome=StageOutcome.FAILED,
                    artifact_path=None,
                    message=f"plan review pass {pass_idx} failed: {rev.stderr.strip()}",
                )

            # The reviewer may also need an answer from the human.
            if has_blocker(ctx.state_dir):
                return blocked_result(StageName.PLAN, ctx.state_dir)
            report = artifact_result(StageName.PLAN, review_md_host, previous)
            if report.outcome is StageOutcome.FAILED:
                return report
            verdict = parse_verdict(read_artifact(review_md_host))
            if verdict == "APPROVED":
                return draft_result
            if verdict is None:
                return StageResult(StageOutcome.FAILED, review_md_host, "Invalid plan verdict")
            if pass_idx == ctx.config.max_plan_reviews:
                break

            revise_prompt = (
                f"Revise {plan_md} to address every item in {review_md}. "
                f"If a reviewer question requires human input, write {blocked_md} and stop."
            )
            revise_result = run_headless_with_escalation(
                ctx, StageName.PLAN, sandbox, revise_prompt, plan_md_host
            )
            if revise_result.outcome is not StageOutcome.DONE:
                return revise_result

        return StageResult(
            outcome=StageOutcome.FAILED,
            artifact_path=review_md_host,
            message="Plan review limit reached without approval",
        )
