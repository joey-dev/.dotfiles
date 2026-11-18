"""Stage 8: Human Check & Retro — interactive review and KB/skill diff proposal."""

from __future__ import annotations

import uuid

from claude_workflow.claude_runner import run_claude_interactive
from claude_workflow.config import StageName
from claude_workflow.sandbox import sandbox_paths
from claude_workflow.stages.base import (
    StageContext,
    StageOutcome,
    StageResult,
    artifact_result,
    artifact_stamp,
    build_stage_sandbox,
)
from claude_workflow.state import save_state


class RetroStage:
    """Present verification/review results and propose KB or skill updates."""

    def run(self, ctx: StageContext) -> StageResult:
        """Execute Stage 8 (Retro) interactively."""
        artifact = ctx.state_dir / "08-retro.md"
        existing_sid = ctx.state.session_ids.get(StageName.RETRO.value)
        resume = existing_sid is not None
        session_id = existing_sid if existing_sid is not None else str(uuid.uuid4())

        if not resume:
            ctx.state.session_ids[StageName.RETRO.value] = session_id
            save_state(ctx.state_dir, ctx.state)

        sandbox = build_stage_sandbox(
            ctx,
            StageName.RETRO,
            repo_dir=None,
            kb_dir=ctx.config.kb_path,
            workdir=ctx.state_dir,
        )
        paths = sandbox_paths(sandbox)
        print(f"Review the worktree at {ctx.state.worktree_path}")
        print(f"Diff: {ctx.state_dir / 'diff.patch'}")
        feedback = ctx.state_dir / "feedback.md"
        print(f"Share feedback in this session or write it to {feedback}")
        prompt = (
            f"Review {paths.notes_dir / '06-verify.md'} and "
            f"{paths.notes_dir / '07-review.md'} "
            f"with the user. Inspect {paths.notes_dir / 'diff.patch'} and read "
            f"{paths.notes_dir / 'feedback.md'} if present. Capture human feedback before "
            "proposing concrete diffs to the workflow skills in ~/skills "
            f"or the personal KB in {paths.notes_dir / '08-retro.md'}."
        )
        previous = None if resume else artifact_stamp(artifact)
        rc = run_claude_interactive(
            ctx.config.stages[StageName.RETRO],
            sandbox,
            prompt,
            session_id=session_id,
            resume=resume,
        )
        if rc != 0:
            if rc not in (-2, 130):
                ctx.state.session_ids.pop(StageName.RETRO.value, None)
                save_state(ctx.state_dir, ctx.state)
            return StageResult(
                outcome=StageOutcome.FAILED,
                artifact_path=None,
                message=f"retro interactive session exited with code {rc}",
            )
        return artifact_result(StageName.RETRO, artifact, previous)
