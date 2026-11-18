"""Regression coverage for workflow boundaries and checkpoint recovery."""

from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from claude_workflow.config import STAGE_ORDER, StageName, default_config
from claude_workflow.pipeline import run_pipeline
from claude_workflow.stages.base import StageContext, StageOutcome, StageResult
from claude_workflow.state import TicketState


class WorkflowRegressionTests(TestCase):
    def test_abort_keeps_approval_pending_for_next_invocation(self) -> None:
        calls: list[StageName] = []

        class Runner:
            def run(self, ctx):
                calls.append(ctx.state.current_stage)
                return StageResult(StageOutcome.DONE, None, "")

        with TemporaryDirectory() as directory:
            config = replace(default_config(), state_base=Path(directory))
            runners = {stage: Runner() for stage in STAGE_ORDER}
            with patch("builtins.input", side_effect=["a", "a"]):
                self.assertEqual(run_pipeline("PROJ-1", config, stage_runners=runners), 1)
                self.assertEqual(run_pipeline("PROJ-1", config, stage_runners=runners), 1)

        self.assertEqual(calls, [StageName.INTAKE])

    def test_successful_intake_requires_new_ticket_artifact(self) -> None:
        from claude_workflow.claude_runner import ClaudeResult
        from claude_workflow.stages.intake import IntakeStage

        with TemporaryDirectory() as directory:
            config = replace(default_config(), state_base=Path(directory))
            ticket_dir = config.state_base / "PROJ-1"
            ticket_dir.mkdir()
            mcp = Path(directory) / "mcp.json"
            mcp.write_text("{}")
            config.stages[StageName.INTAKE] = replace(
                config.stages[StageName.INTAKE], mcp_config=mcp
            )
            (ticket_dir / "01-ticket.md").write_text("old ticket")
            with patch(
                "claude_workflow.stages.base.run_claude_headless",
                return_value=ClaudeResult(0, "", "", None),
            ):
                ctx = StageContext("PROJ-1", config, TicketState("PROJ-1"), ticket_dir)
                result = IntakeStage().run(ctx)
            self.assertEqual(result.outcome, StageOutcome.FAILED)
            self.assertEqual((ticket_dir / "01-ticket.md").read_text(), "old ticket")

    def test_invalid_ticket_id_does_not_create_state_directory(self) -> None:
        with TemporaryDirectory() as directory:
            config = replace(default_config(), state_base=Path(directory) / "state")
            self.assertEqual(run_pipeline("../outside", config, auto=True), 1)
            self.assertFalse((Path(directory) / "outside").exists())

    def test_verification_requires_checks(self) -> None:
        from claude_workflow.stages.verify import VerifyStage

        with TemporaryDirectory() as directory:
            path = Path(directory)
            config = default_config()
            state = TicketState("PROJ-1", worktree_path=path)
            result = VerifyStage().run(StageContext("PROJ-1", config, state, path))
            self.assertEqual(result.outcome, StageOutcome.FAILED)

    def test_verification_runs_configured_check_inside_network_isolation(self) -> None:
        from subprocess import CompletedProcess

        from claude_workflow.stages.verify import VerifyStage

        with TemporaryDirectory() as directory:
            path = Path(directory)
            worktree = path / "worktree"
            worktree.mkdir()
            config = replace(
                default_config(), verify_commands=("printf verified",), state_base=path / "base"
            )
            state = TicketState("PROJ-1", worktree_path=worktree, base_commit="base")
            ctx = StageContext("PROJ-1", config, state, path)
            (path / "tests.txt").write_text("")
            with (
                patch("claude_workflow.stages.verify.capture_diff", return_value="patch"),
                patch("claude_workflow.stages.verify.changed_paths", return_value=[]),
                patch(
                    "claude_workflow.docker_stack.subprocess.run",
                    return_value=CompletedProcess([], 0, "verified", ""),
                ) as launch,
            ):
                result = VerifyStage().run(ctx)

            self.assertEqual(result.outcome, StageOutcome.DONE)
            args = launch.call_args.args[0]
            self.assertEqual(args[0], "bwrap")
            self.assertIn("--unshare-net", args)
            self.assertEqual(args[-3:], ["sh", "-c", "printf verified"])
            self.assertIn("verified", (path / "06-verify.md").read_text())
            self.assertIsNotNone(state.verified_diff)

    def test_only_stage_stops_before_the_next_runner(self) -> None:
        calls: list[StageName | None] = []

        class Runner:
            def run(self, ctx: StageContext) -> StageResult:
                calls.append(ctx.state.current_stage)
                return StageResult(StageOutcome.DONE, None, "")

        with TemporaryDirectory() as directory:
            config = replace(default_config(), state_base=Path(directory))
            self.assertEqual(
                run_pipeline(
                    "PROJ-1", config, auto=True, only_stage=StageName.INTAKE,
                    stage_runners={StageName.INTAKE: Runner()},
                ),
                0,
            )
            self.assertEqual(calls, [StageName.INTAKE])

    def test_clean_but_changed_branch_cannot_pass_finalization(self) -> None:
        from claude_workflow.git_host import diff_digest
        from claude_workflow.state import load_state, save_state

        with TemporaryDirectory() as directory:
            path = Path(directory)
            config = replace(default_config(), state_base=path, worktree_base=path / "worktrees")
            ticket_dir = path / "PROJ-1"
            state = TicketState(
                "PROJ-1", current_stage=StageName.RETRO, approval_pending=True,
                worktree_path=config.worktree_base / "PROJ-1", base_commit="base",
                verified_diff=diff_digest("expected change"),
            )
            save_state(ticket_dir, state)
            with (
                patch("claude_workflow.pipeline.capture_diff", return_value="different change"),
                patch("claude_workflow.pipeline.is_dirty", return_value=False),
                patch("claude_workflow.pipeline.commit_stage") as commit,
            ):
                self.assertEqual(run_pipeline("PROJ-1", config, auto=True), 1)
            commit.assert_not_called()
            self.assertTrue(load_state(ticket_dir, "PROJ-1").approval_pending)

    def test_missing_project_flake_does_not_block_intake_sandbox(self) -> None:
        from claude_workflow.stages.base import build_stage_sandbox

        with TemporaryDirectory() as directory:
            path = Path(directory)
            config = replace(default_config(), flake_path=path / "absent-flake")
            ctx = StageContext("PROJ-1", config, TicketState("PROJ-1"), path)
            sandbox = build_stage_sandbox(
                ctx, StageName.INTAKE, repo_dir=None, kb_dir=None, workdir=path
            )
            self.assertIsNone(sandbox.flake_dir)

    def test_diff_digest_ignores_file_section_order(self) -> None:
        from claude_workflow.git_host import diff_digest

        first = "diff --git a/one b/one\n+one\n"
        second = "diff --git a/two b/two\n+two\n"
        self.assertEqual(diff_digest(first + second), diff_digest(second + first))
        self.assertNotEqual(diff_digest(first + second), diff_digest(first))
