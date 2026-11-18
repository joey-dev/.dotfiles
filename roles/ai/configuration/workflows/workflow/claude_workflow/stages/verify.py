"""Stage 6: Verify — run configured linters and unit tests on the worktree."""

from __future__ import annotations

import subprocess
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory

from claude_workflow.config import StageName
from claude_workflow.git_host import capture_diff, diff_digest
from claude_workflow.sandbox import build_bwrap_command
from claude_workflow.stages.base import (
    StageContext,
    StageOutcome,
    StageResult,
    build_stage_sandbox,
    write_artifact,
)


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
        flake = ctx.config.flake_path
        use_flake = flake is not None and flake.exists()
        before = capture_diff(workdir, ctx.state.base_commit)

        with TemporaryDirectory(prefix="cw-verify-") as scratch:
            sandbox = replace(sandbox, state_dir=Path(scratch), skills_dirs=(), mcp_config=None)
            for cmd in ctx.config.verify_commands:
                argv = build_bwrap_command(sandbox, ["sh", "-c", cmd])
                if use_flake:
                    argv = ["nix", "develop", str(flake), "--command", *argv]
                proc = subprocess.run(argv, check=False, capture_output=True, text=True)
                status = "PASS" if proc.returncode == 0 else f"FAIL (exit {proc.returncode})"
                if proc.returncode != 0:
                    all_passed = False
                output = (proc.stdout + proc.stderr).rstrip()
                sections.append(f"## `{cmd}` — {status}\n\n```text\n{output}\n```\n")

        write_artifact(artifact, "\n".join(sections))
        if not all_passed:
            return StageResult(
                outcome=StageOutcome.FAILED,
                artifact_path=artifact,
                message=f"verification failed; see {artifact}",
            )
        if capture_diff(workdir, ctx.state.base_commit) != before:
            return StageResult(
                StageOutcome.FAILED, artifact, "Verification changed the worktree diff."
            )
        ctx.state.verified_diff = diff_digest(before)
        return StageResult(
            outcome=StageOutcome.DONE,
            artifact_path=artifact,
            message="verify completed",
        )
