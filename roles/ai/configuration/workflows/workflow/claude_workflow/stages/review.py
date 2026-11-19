"""Stage 7: Code Review — two focused read-only lenses over diff.patch."""

from __future__ import annotations

import hashlib
from pathlib import Path

from claude_workflow.catalogue import command_catalogue
from claude_workflow.claude_runner import run_claude_headless
from claude_workflow.config import StageName
from claude_workflow.git_host import capture_diff, diff_digest
from claude_workflow.sandbox import sandbox_paths
from claude_workflow.stages.base import (
    StageContext,
    StageOutcome,
    StageResult,
    artifact_result,
    artifact_stamp,
    build_stage_sandbox,
    parse_verdict,
    read_artifact,
    write_artifact,
)
from claude_workflow.tests_file import TESTS_FILE

_LENSES: tuple[tuple[str, str], ...] = (
    (
        "correctness",
        "Review diff.patch strictly for logic bugs, edge cases, error handling, "
        "missing tests, and regressions against 01-ticket.md and 04-plan.md. "
        "If you think a test will fail, append a line for it to {tests_file} under "
        "'# suggested by review' and report it as a finding.",
    ),
    (
        "conventions",
        "Review diff.patch strictly for codebase conventions, readability, "
        "maintainability, and unnecessary complexity.",
    ),
)


def _file_hash(path: Path) -> str | None:
    """Hash a file's bytes; None when it is missing."""
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


class ReviewStage:
    """Run Correctness and Conventions review lenses and combine into 07-review.md."""

    def run(self, ctx: StageContext) -> StageResult:
        """Capture diff.patch from base_commit and run 2 read-only review passes."""
        worktree = ctx.state.worktree_path
        base_ref = ctx.state.base_commit
        if worktree is None or not worktree.is_dir() or not base_ref:
            return StageResult(StageOutcome.FAILED, None, "Review requires a worktree and base.")
        diff_patch_host = ctx.state_dir / "diff.patch"
        diff_text = capture_diff(worktree, base_ref=base_ref)
        if diff_digest(diff_text) != ctx.state.verified_diff:
            return StageResult(StageOutcome.FAILED, None, "Worktree changed or was never verified.")
        write_artifact(diff_patch_host, diff_text)

        sandbox = build_stage_sandbox(
            ctx,
            StageName.REVIEW,
            repo_dir=worktree,
            kb_dir=ctx.config.kb_path,
            workdir=worktree,
        )
        paths = sandbox_paths(sandbox)
        stage_cfg = ctx.config.stages[StageName.REVIEW]
        tests_host = ctx.state_dir / TESTS_FILE
        tests_before = _file_hash(tests_host)
        combined_sections: list[str] = ["# Automated Code Review\n"]
        blocking_findings = False

        for lens_name, focus in _LENSES:
            lens_host = ctx.state_dir / f"07-review-{lens_name}.md"
            lens_sandbox = paths.notes_dir / f"07-review-{lens_name}.md"
            focus_text = focus.format(tests_file=paths.notes_dir / TESTS_FILE)
            catalogue = command_catalogue(ctx.config.commands) if lens_name == "correctness" else ""
            prompt = (
                f"Read {paths.notes_dir / 'diff.patch'}, "
                f"{paths.notes_dir / '01-ticket.md'}, and "
                f"{paths.notes_dir / '04-plan.md'}. Focus: {focus_text} "
                f"Write findings to {lens_sandbox}. Start with CHANGES_REQUESTED if issues "
                "need to be fixed before acceptance, or APPROVED otherwise."
                + (f"\n\n{catalogue}" if catalogue else "")
            )
            previous = artifact_stamp(lens_host)
            res = run_claude_headless(
                stage_cfg, sandbox, prompt, timeout=ctx.config.headless_timeout
            )
            if res.returncode != 0:
                return StageResult(
                    outcome=StageOutcome.FAILED,
                    artifact_path=None,
                    message=f"review ({lens_name}) failed: {res.stderr.strip()}",
                )
            report = artifact_result(StageName.REVIEW, lens_host, previous)
            if report.outcome is StageOutcome.FAILED:
                return report
            body = read_artifact(lens_host)
            verdict = parse_verdict(body)
            if verdict is None:
                return StageResult(StageOutcome.FAILED, lens_host, "Invalid review verdict")
            blocking_findings |= verdict == "CHANGES_REQUESTED"
            combined_sections.append(f"## Lens: {lens_name.title()}\n\n{body.strip()}\n")

        artifact = ctx.state_dir / "07-review.md"
        write_artifact(artifact, "\n".join(combined_sections))
        if _file_hash(tests_host) != tests_before:
            return StageResult(
                StageOutcome.NEEDS_FIX, artifact, f"Review suggested tests in {TESTS_FILE}"
            )
        if blocking_findings:
            return StageResult(
                StageOutcome.NEEDS_FIX, artifact, f"Review requested changes; see {artifact}"
            )
        return StageResult(
            outcome=StageOutcome.DONE,
            artifact_path=artifact,
            message="review completed",
        )
