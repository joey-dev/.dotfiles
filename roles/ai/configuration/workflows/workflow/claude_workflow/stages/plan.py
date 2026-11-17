"""Stage 4: Plan — draft implementation plan with capped reviewer passes."""

from __future__ import annotations

from claude_workflow.claude_runner import run_claude_headless
from claude_workflow.config import StageName
from claude_workflow.stages.base import (
    StageContext,
    StageOutcome,
    StageResult,
    blocked_questions_path,
    build_stage_sandbox,
    read_artifact,
    run_headless_with_escalation,
)


class PlanStage:
    """Draft 04-plan.md and run up to max_plan_reviews adversarial review passes."""

    def run(self, ctx: StageContext) -> StageResult:
        """Execute Stage 4 (Plan) and write 04-plan.md."""
        plan_md = ctx.state_dir / "04-plan.md"
        review_md = ctx.state_dir / "04-plan-review.md"
        sandbox = build_stage_sandbox(
            ctx,
            StageName.PLAN,
            repo_dir=ctx.config.repo_path,
            kb_dir=ctx.config.kb_path,
            workdir=ctx.config.repo_path,
        )

        draft_prompt = (
            f"Read {ctx.state_dir / '01-ticket.md'}, {ctx.state_dir / '02-findings.md'}, and "
            f"{ctx.state_dir / '03-qa.md'}. Write a concrete, step-by-step implementation and "
            f"test plan to {plan_md}. If you hit a genuine unknown, write {blocked_questions_path(ctx.state_dir)} "
            f"and stop instead of guessing."
        )
        draft_result = run_headless_with_escalation(
            ctx, StageName.PLAN, sandbox, draft_prompt, plan_md
        )
        if draft_result.outcome is not StageOutcome.DONE:
            return draft_result

        stage_cfg = ctx.config.stages[StageName.PLAN]
        for pass_idx in range(1, ctx.config.max_plan_reviews + 1):
            review_prompt = (
                f"Review {plan_md} critically (pass {pass_idx}/{ctx.config.max_plan_reviews}) "
                f"against {ctx.state_dir / '01-ticket.md'} and {ctx.state_dir / '03-qa.md'}. "
                f"Write your review to {review_md}. Start the file with 'APPROVED' if the plan "
                f"is ready, or 'CHANGES_REQUESTED' followed by concrete fixes."
            )
            rev = run_claude_headless(stage_cfg, sandbox, review_prompt)
            if rev.returncode != 0:
                return StageResult(
                    outcome=StageOutcome.FAILED,
                    artifact_path=None,
                    message=f"plan review pass {pass_idx} failed: {rev.stderr.strip()}",
                )

            review_text = read_artifact(review_md).strip()
            if review_text.startswith("APPROVED"):
                break

            revise_prompt = (
                f"Revise {plan_md} to address every item in {review_md}. "
                f"If a reviewer question requires human input, write "
                f"{blocked_questions_path(ctx.state_dir)} and stop."
            )
            revise_result = run_headless_with_escalation(
                ctx, StageName.PLAN, sandbox, revise_prompt, plan_md
            )
            if revise_result.outcome is not StageOutcome.DONE:
                return revise_result

        return StageResult(
            outcome=StageOutcome.DONE,
            artifact_path=plan_md,
            message="plan completed",
        )
