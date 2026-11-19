"""Stage 6: Verify — run the `verify` entries, then the ticket's tests.txt, on the worktree.

Every command goes through `commands.render` and `runners.run`. `verify` entries come
from the trusted config (they get the Verify cache); tests.txt lines come from Claude,
so their values are validated against each parameter's pattern and get no cache.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from pathlib import Path
from tempfile import TemporaryDirectory

from claude_workflow.catalogue import describe_values
from claude_workflow.commands import ChangedFiles, Skip, render
from claude_workflow.config import StageName
from claude_workflow.env import sandbox_env
from claude_workflow.git_host import capture_diff, changed_files, changed_paths, diff_digest
from claude_workflow.runners import HostStop, RunContext, run
from claude_workflow.stages.base import (
    StageContext,
    StageOutcome,
    StageResult,
    build_stage_sandbox,
    read_artifact,
    write_artifact,
)
from claude_workflow.tests_file import TESTS_FILE, parse_tests_file

SKIPPED_NO_FILES = "SKIPPED (no changed files)"
SKIPPED_HOST_STOP = "SKIPPED (host commands stopped)"


def _fenced(text: str) -> str:
    """`text` in a code fence longer than any backtick run inside it, so it can't close."""
    longest = max((len(run) for run in re.findall(r"`+", text)), default=0)
    fence = "`" * max(3, longest + 1)
    return f"{fence}text\n{text}\n{fence}\n"


def _section(label: str, status: str, output: str) -> str:
    """One artifact section: always the status and the full output."""
    return f"## `{label}` — {status}\n\n{_fenced(output)}"


@dataclass(frozen=True)
class _Job:
    """One command to run: from `verify` (trusted) or from tests.txt."""

    name: str
    values: dict[str, str | ChangedFiles]
    trusted: bool


@dataclass
class _Results:
    sections: list[str]
    failed: bool = False
    stop: str | None = None


def _run_job(job: _Job, run_ctx: RunContext, changed: list[str], results: _Results) -> None:
    """Run one job. When it started the compose stack and `up` passed, the `up` output
    gets its own section before the job's (a failed `up` is in the job's section)."""
    stack = run_ctx.stack
    first_up = stack.result is None
    at = len(results.sections)
    _run_one(job, run_ctx, changed, results)
    if first_up and stack.result is not None and stack.result[0] == "PASS":
        status, output = stack.result
        results.sections.insert(
            at, _section("docker compose up", status, f"$ {stack.command}\n{output}")
        )


def _run_one(job: _Job, run_ctx: RunContext, changed: list[str], results: _Results) -> None:
    """Render and run one job; record its section. Never raises for a bad command."""
    label = describe_values(job.name, job.values)
    cmd = run_ctx.config.commands.get(job.name)
    if cmd is None:
        results.failed = True
        results.sections.append(
            _section(label, "FAIL (invalid command)", f"unknown command {job.name!r}")
        )
        return
    if results.stop is not None and cmd.run_in != "sandbox":
        results.sections.append(_section(label, SKIPPED_HOST_STOP, results.stop))
        return
    try:
        argv = render(cmd, job.values, changed, from_tests_file=not job.trusted)
        status, output = run(cmd, argv, replace(run_ctx, trusted=job.trusted))
    except Skip as exc:
        results.sections.append(_section(label, SKIPPED_NO_FILES, str(exc)))
        return
    except HostStop as exc:
        results.stop = f"Host commands stopped: {exc}. Run them by hand."
        results.sections.append(f"## Host commands stopped\n\n`{label}`:\n\n{_fenced(str(exc))}")
        return
    except ValueError as exc:
        results.failed = True
        results.sections.append(_section(label, "FAIL (invalid command)", str(exc)))
        return
    results.failed = results.failed or status != "PASS"
    results.sections.append(_section(label, status, f"$ {argv[2]}\n{output}"))


def _run_jobs(
    ctx: StageContext, workdir: Path, base: str, jobs: list[_Job], changed: list[str]
) -> _Results:
    """Run every job in order; host stops are recorded, not raised."""
    results = _Results(sections=[])
    if not jobs:
        return results
    sandbox = build_stage_sandbox(
        ctx, StageName.VERIFY, repo_dir=workdir, kb_dir=None, workdir=workdir
    )
    with TemporaryDirectory(prefix="cw-verify-") as scratch:
        sandbox = replace(sandbox, state_dir=Path(scratch), skills_dirs=(), mcp_config=None)
        flake = sandbox.flake_dir if sandbox.flake_dir and sandbox.flake_dir.exists() else None
        run_ctx = RunContext(
            config=ctx.config,
            worktree=workdir,
            base_commit=base,
            sandbox=sandbox,
            sandbox_env=sandbox_env(flake),
        )
        for job in jobs:
            _run_job(job, run_ctx, changed, results)
    return results


class VerifyStage:
    """Run the `verify` entries and tests.txt, and write 06-verify.md."""

    def run(self, ctx: StageContext) -> StageResult:
        """Run the checks, record every result, and decide the outcome.

        Any failed check → NEEDS_FIX (also when host commands had to stop; the
        artifact says so). Only a host stop → NEEDS_HUMAN. Skips count as neither.
        """
        workdir = ctx.state.worktree_path
        base = ctx.state.base_commit
        artifact = ctx.state_dir / "06-verify.md"
        if workdir is None or not workdir.is_dir() or not base:
            message = "Verification requires a worktree and base."
            return StageResult(StageOutcome.FAILED, None, message)
        before = capture_diff(workdir, base)

        tests_path = ctx.state_dir / TESTS_FILE
        if tests_path.is_symlink() or not tests_path.is_file():
            write_artifact(artifact, f"# Verification\n\nNo {TESTS_FILE} found.\n")
            ctx.state.verified_diff = diff_digest(before)
            return StageResult(
                StageOutcome.NEEDS_FIX, artifact, f"write {TESTS_FILE} (see 04-plan.md)"
            )
        lines, errors = parse_tests_file(read_artifact(tests_path), ctx.config.commands)
        sections = ["# Verification\n"]
        if not lines and not errors:
            sections.append(f"Note: {TESTS_FILE} lists no tests.\n")
        sections += [_section(TESTS_FILE, "FAIL (invalid line)", error) for error in errors]

        jobs = [_Job(e.run, dict(e.values), trusted=True) for e in ctx.config.verify]
        jobs += [_Job(t.command, dict(t.values), trusted=False) for t in lines]
        results = _run_jobs(ctx, workdir, base, jobs, changed_paths(workdir, base))
        sections += results.sections

        write_artifact(artifact, "\n".join(sections))
        after = capture_diff(workdir, base)
        if after != before:
            files = ", ".join(changed_files(before, after)) or "unknown files"
            return StageResult(
                StageOutcome.FAILED,
                artifact,
                f"Verification changed the worktree diff: {files}. "
                "Add generated files to .gitignore.",
            )
        # Remember what was checked, also on failure, so "continue anyway" can go on.
        ctx.state.verified_diff = diff_digest(before)
        if results.failed or errors:
            message = f"verification failed; see {artifact}"
            if results.stop is not None:
                message += f". Also: {results.stop}"
            return StageResult(StageOutcome.NEEDS_FIX, artifact, message)
        if results.stop is not None:
            return StageResult(StageOutcome.NEEDS_HUMAN, artifact, results.stop)
        return StageResult(StageOutcome.DONE, artifact, "verify completed")
