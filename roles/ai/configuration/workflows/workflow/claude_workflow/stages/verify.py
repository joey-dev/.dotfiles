"""Stage 6: Verify — run configured linters and unit tests on the worktree."""

from __future__ import annotations

import subprocess

from claude_workflow.stages.base import StageContext, StageOutcome, StageResult


class VerifyStage:
    """Execute verify_commands from WorkflowConfig and write 06-verify.md."""

    def run(self, ctx: StageContext) -> StageResult:
        """Run configured verification commands and record results."""
        workdir = ctx.state.worktree_path or ctx.config.repo_path
        artifact = ctx.state_dir / "06-verify.md"

        if not ctx.config.verify_commands:
            artifact.write_text("# Verification\n\nNo verify_commands configured.\n", encoding="utf-8")
            return StageResult(
                outcome=StageOutcome.DONE,
                artifact_path=artifact,
                message="verify skipped (no verify_commands configured)",
            )

        sections: list[str] = ["# Verification\n"]
        all_passed = True

        for cmd in ctx.config.verify_commands:
            proc = subprocess.run(
                cmd,
                shell=True,
                cwd=workdir,
                check=False,
                capture_output=True,
                text=True,
            )
            status = "PASS" if proc.returncode == 0 else f"FAIL (exit {proc.returncode})"
            if proc.returncode != 0:
                all_passed = False
            sections.append(
                f"## `{cmd}` — {status}\n\n"
                f"```text\n{proc.stdout}{proc.stderr}```\n"
            )

        artifact.write_text("\n".join(sections), encoding="utf-8")
        if not all_passed:
            return StageResult(
                outcome=StageOutcome.FAILED,
                artifact_path=artifact,
                message=f"verification failed; see {artifact}",
            )
        return StageResult(
            outcome=StageOutcome.DONE,
            artifact_path=artifact,
            message="verify completed",
        )
