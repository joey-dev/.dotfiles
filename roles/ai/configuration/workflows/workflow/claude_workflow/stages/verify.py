"""Stage 6: Verify — run configured linters and unit tests on the worktree."""

from __future__ import annotations

import subprocess
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory

from claude_workflow.config import StageName
from claude_workflow.git_host import capture_diff, changed_files, diff_digest
from claude_workflow.sandbox import build_bwrap_command
from claude_workflow.stages.base import (
    StageContext,
    StageOutcome,
    StageResult,
    build_stage_sandbox,
    write_artifact,
)


def _run_check(argv: list[str], timeout: int) -> tuple[str, str]:
    """Run one verify command; return (status, output)."""
    try:
        proc = subprocess.run(argv, check=False, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return f"FAIL (timeout after {timeout}s)", ""
    status = "PASS" if proc.returncode == 0 else f"FAIL (exit {proc.returncode})"
    return status, (proc.stdout + proc.stderr).rstrip()


class VerifyStage:
    """Execute verify_commands from WorkflowConfig and write 06-verify.md."""

    def run(self, ctx: StageContext) -> StageResult:
        """Run configured verification commands and record results."""
        workdir = ctx.state.worktree_path
        artifact = ctx.state_dir / "06-verify.md"

        if not ctx.config.verify_commands:
            write_artifact(artifact, "# Verification\n\nNo verify_commands configured.\n")
            return StageResult(
                outcome=StageOutcome.FAILED,
                artifact_path=artifact,
                message="Configure verify_commands before verification.",
            )

        if workdir is None or not workdir.is_dir() or not ctx.state.base_commit:
            return StageResult(StageOutcome.FAILED, None, "Verification requires a worktree and base.")

        sandbox = build_stage_sandbox(
            ctx, StageName.VERIFY, repo_dir=workdir, kb_dir=None, workdir=workdir
        )
        sections: list[str] = ["# Verification\n"]
        all_passed = True
        before = capture_diff(workdir, ctx.state.base_commit)

        with TemporaryDirectory(prefix="cw-verify-") as scratch:
            sandbox = replace(sandbox, state_dir=Path(scratch), skills_dirs=(), mcp_config=None)
            for cmd in ctx.config.verify_commands:
                argv = build_bwrap_command(sandbox, ["sh", "-c", cmd])
                status, output = _run_check(argv, ctx.config.verify_timeout)
                if status != "PASS":
                    all_passed = False
                sections.append(f"## `{cmd}` — {status}\n\n```text\n{output}\n```\n")

        write_artifact(artifact, "\n".join(sections))
        after = capture_diff(workdir, ctx.state.base_commit)
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
        if not all_passed:
            return StageResult(
                outcome=StageOutcome.NEEDS_FIX,
                artifact_path=artifact,
                message=f"verification failed; see {artifact}",
            )
        return StageResult(
            outcome=StageOutcome.DONE,
            artifact_path=artifact,
            message="verify completed",
        )
