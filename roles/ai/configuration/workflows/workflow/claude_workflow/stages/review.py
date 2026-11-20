"""Stage 7: Code Review — two read-only lenses over diff.patch, then a validation pass.

When a lens blocks, a separate run checks only its blocking findings against the code.
It does not see the lens reasoning, so it is not anchored on it. Findings it rejects no
longer block the ticket.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

from claude_workflow.catalogue import command_catalogue
from claude_workflow.claude_runner import run_claude_headless
from claude_workflow.config import StageConfig, StageName
from claude_workflow.git_host import capture_diff, diff_digest
from claude_workflow.sandbox import SandboxSpec, sandbox_paths
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
        "missing tests, and regressions against 01-ticket.md (as changed by 03-qa.md) "
        "and 04-plan.md. "
        "If you think a test will fail, append a line for it to {tests_file} under "
        "'# suggested by review' and report it as a finding.",
    ),
    (
        "conventions",
        "Review diff.patch strictly for codebase conventions, readability, "
        "maintainability, and unnecessary complexity.",
    ),
)

BLOCKING_FILE = "07-review-blocking.md"
VALIDATION_FILE = "07-review-validation.md"

_BLOCKING_HEADING = re.compile(r"^#{1,6}[ \t]*[*_`]*Blocking\b.*$", re.IGNORECASE | re.MULTILINE)
_ANY_HEADING = re.compile(r"^#{1,6}[ \t]", re.MULTILINE)


def _file_hash(path: Path) -> str | None:
    """Hash a file's bytes; None when it is missing."""
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def blocking_section(report: str) -> str:
    """The findings under a lens report's "Blocking" heading.

    Without that heading (or with an empty one), fall back to the whole report minus
    its verdict line, so a finding is never dropped because of a formatting slip.
    """
    match = _BLOCKING_HEADING.search(report)
    if match is not None:
        rest = report[match.end() :]
        end = _ANY_HEADING.search(rest)
        section = (rest[: end.start()] if end else rest).strip()
        if section:
            return section
    lines = report.strip().splitlines()
    return "\n".join(lines[1:]).strip()


def _run_report(
    ctx: StageContext,
    stage_cfg: StageConfig,
    sandbox: SandboxSpec,
    prompt: str,
    report_host: Path,
    label: str,
) -> StageResult | str:
    """Run one headless pass that must write report_host; return its body or a failure."""
    previous = artifact_stamp(report_host)
    res = run_claude_headless(stage_cfg, sandbox, prompt, timeout=ctx.config.headless_timeout)
    if res.returncode != 0:
        message = f"review ({label}) failed: {res.stderr.strip()}"
        return StageResult(StageOutcome.FAILED, None, message)
    report = artifact_result(StageName.REVIEW, report_host, previous)
    if report.outcome is StageOutcome.FAILED:
        return report
    return read_artifact(report_host)


class ReviewStage:
    """Run the review lenses, validate blocking findings, and combine into 07-review.md."""

    def run(self, ctx: StageContext) -> StageResult:
        """Capture diff.patch from base_commit, run 2 lenses, then validate any blockers."""
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
        lens_sections: list[str] = []
        blocking: list[tuple[str, str]] = []

        for lens_name, focus in _LENSES:
            lens_file = f"07-review-{lens_name}.md"
            focus_text = focus.format(tests_file=paths.notes_dir / TESTS_FILE)
            catalogue = command_catalogue(ctx.config.commands) if lens_name == "correctness" else ""
            prompt = (
                f"Read {paths.notes_dir / 'diff.patch'}, "
                f"{paths.notes_dir / '01-ticket.md'}, "
                f"{paths.notes_dir / '03-qa.md'}, and "
                f"{paths.notes_dir / '04-plan.md'}. Focus: {focus_text} "
                f"Write findings to {paths.notes_dir / lens_file}. Start with CHANGES_REQUESTED "
                "if issues need to be fixed before acceptance, or APPROVED otherwise."
                + (f"\n\n{catalogue}" if catalogue else "")
            )
            lens_host = ctx.state_dir / lens_file
            body = _run_report(ctx, stage_cfg, sandbox, prompt, lens_host, lens_name)
            if isinstance(body, StageResult):
                return body
            verdict = parse_verdict(body)
            if verdict is None:
                return StageResult(StageOutcome.FAILED, lens_host, "Invalid review verdict")
            if verdict == "CHANGES_REQUESTED":
                blocking.append((lens_name, blocking_section(body)))
            lens_sections.append(f"## Lens: {lens_name.title()}\n\n{body.strip()}\n")

        validation_section: list[str] = []
        if blocking:
            findings = "\n\n".join(f"## {name.title()}\n\n{text}\n" for name, text in blocking)
            write_artifact(ctx.state_dir / BLOCKING_FILE, findings)
            prompt = (
                f"Validation pass. {paths.notes_dir / BLOCKING_FILE} lists blocking findings "
                f"from other reviewers of {paths.notes_dir / 'diff.patch'}. Read it, the diff, "
                f"{paths.notes_dir / '01-ticket.md'} and {paths.notes_dir / '03-qa.md'}, "
                "then check each finding against the "
                "code in the repository. Do not look for new issues. "
                f"Write {paths.notes_dir / VALIDATION_FILE}: the first line is CHANGES_REQUESTED "
                "if at least one finding is CONFIRMED, otherwise APPROVED. Then one line per "
                "finding: CONFIRMED or REJECTED, the finding's location, and why."
            )
            validation_host = ctx.state_dir / VALIDATION_FILE
            body = _run_report(ctx, stage_cfg, sandbox, prompt, validation_host, "validation")
            if isinstance(body, StageResult):
                return body
            verdict = parse_verdict(body)
            if verdict is None:
                return StageResult(
                    StageOutcome.FAILED, validation_host, "Invalid validation verdict"
                )
            validation_section.append(
                "## Validation\n\nFix only findings marked CONFIRMED here; REJECTED findings "
                f"were checked against the code and are not real.\n\n{body.strip()}\n"
            )
            if verdict == "APPROVED":
                blocking = []

        artifact = ctx.state_dir / "07-review.md"
        write_artifact(
            artifact, "\n".join(["# Automated Code Review\n", *validation_section, *lens_sections])
        )
        if _file_hash(tests_host) != tests_before:
            return StageResult(
                StageOutcome.NEEDS_FIX, artifact, f"Review suggested tests in {TESTS_FILE}"
            )
        if blocking:
            return StageResult(
                StageOutcome.NEEDS_FIX, artifact, f"Review requested changes; see {artifact}"
            )
        message = "review completed" + (
            "; validation rejected all blocking findings" if validation_section else ""
        )
        return StageResult(outcome=StageOutcome.DONE, artifact_path=artifact, message=message)
