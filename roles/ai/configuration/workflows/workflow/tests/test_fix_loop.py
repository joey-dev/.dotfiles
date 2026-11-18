"""Verify and Review can send the ticket back to Implement, a limited number of times."""

from __future__ import annotations

import subprocess
from dataclasses import replace
from pathlib import Path
from typing import Any
from unittest.mock import patch

from claude_workflow.claude_runner import ClaudeResult
from claude_workflow.config import STAGE_ORDER, StageName, WorkflowConfig, default_config
from claude_workflow.pipeline import run_pipeline
from claude_workflow.stages.base import StageContext, StageOutcome, StageProtocol, StageResult
from claude_workflow.stages.implement import ImplementStage
from claude_workflow.stages.verify import VerifyStage
from claude_workflow.state import TicketState, load_state, save_state


class _Scripted:
    """Stub stage: returns the given outcomes in order, then DONE forever."""

    def __init__(self, log: list[tuple[StageName, str | None]], name: StageName,
                 outcomes: list[StageOutcome] | None = None) -> None:
        self._log, self._name, self._outcomes = log, name, list(outcomes or [])

    def run(self, ctx: StageContext) -> StageResult:
        self._log.append((self._name, ctx.state.fix_feedback))
        outcome = self._outcomes.pop(0) if self._outcomes else StageOutcome.DONE
        artifact = ctx.state_dir / ("07-review.md" if self._name is StageName.REVIEW else "x.md")
        return StageResult(outcome, artifact, "")


def _setup(
    tmp_path: Path, review: list[StageOutcome], **config: Any
) -> tuple[WorkflowConfig, list[tuple[StageName, str | None]], dict[StageName, StageProtocol]]:
    cfg = replace(default_config(), state_base=tmp_path, **config)
    log: list[tuple[StageName, str | None]] = []
    runners: dict[StageName, StageProtocol] = {s: _Scripted(log, s) for s in STAGE_ORDER}
    runners[StageName.REVIEW] = _Scripted(log, StageName.REVIEW, review)
    return cfg, log, runners


def _completed_until(cfg: WorkflowConfig, ticket: str, stage: StageName, **fields: Any) -> None:
    done = list(STAGE_ORDER[: STAGE_ORDER.index(stage)])
    save_state(cfg.state_base / ticket, TicketState(ticket, completed_stages=done, **fields))


def _names(log: list[tuple[StageName, str | None]]) -> list[StageName]:
    return [name for name, _ in log]


def test_review_needs_fix_returns_to_implement_with_feedback(tmp_path: Path) -> None:
    cfg, log, runners = _setup(tmp_path, [StageOutcome.NEEDS_FIX])

    assert run_pipeline("PROJ-1", cfg, auto=True, stage_runners=runners) == 0

    i, v, r = StageName.IMPLEMENT, StageName.VERIFY, StageName.REVIEW
    assert _names(log)[4:] == [i, v, r, i, v, r, StageName.RETRO]
    assert log[7] == (i, "07-review.md")
    assert load_state(tmp_path / "PROJ-1", "PROJ-1").fix_feedback is None


def test_fix_loop_stops_after_max_fix_rounds(tmp_path: Path) -> None:
    cfg, log, runners = _setup(tmp_path, [StageOutcome.NEEDS_FIX] * 10, max_fix_rounds=2)

    assert run_pipeline("PROJ-1", cfg, auto=True, stage_runners=runners) == 1

    assert _names(log).count(StageName.IMPLEMENT) == 3


def test_continue_anyway_skips_to_next_stage(tmp_path: Path) -> None:
    cfg, log, runners = _setup(tmp_path, [StageOutcome.NEEDS_FIX])
    _completed_until(cfg, "PROJ-1", StageName.REVIEW)

    with patch("builtins.input", side_effect=["c", "c"]):
        assert run_pipeline("PROJ-1", cfg, stage_runners=runners) == 0

    assert _names(log) == [StageName.REVIEW, StageName.RETRO]


def test_from_stage_plan_clears_fix_feedback(tmp_path: Path) -> None:
    cfg, log, runners = _setup(tmp_path, [])
    _completed_until(cfg, "PROJ-1", StageName.RETRO, fix_feedback="07-review.md", fix_rounds=2)

    run_pipeline("PROJ-1", cfg, from_stage=StageName.PLAN, auto=True, stage_runners=runners)

    assert (StageName.IMPLEMENT, None) in log
    assert load_state(tmp_path / "PROJ-1", "PROJ-1").fix_rounds == 0


def test_only_stage_fix_choice_keeps_feedback_for_from_stage_implement(tmp_path: Path) -> None:
    cfg, log, runners = _setup(tmp_path, [StageOutcome.NEEDS_FIX])
    _completed_until(cfg, "PROJ-1", StageName.REVIEW)

    with patch("builtins.input", side_effect=["f"]):
        rc = run_pipeline("PROJ-1", cfg, only_stage=StageName.REVIEW, stage_runners=runners)

    assert rc == 0
    assert _names(log) == [StageName.REVIEW]
    assert load_state(tmp_path / "PROJ-1", "PROJ-1").fix_feedback == "07-review.md"

    run_pipeline(
        "PROJ-1", cfg, from_stage=StageName.IMPLEMENT, auto=True, stage_runners=runners
    )
    assert log[1] == (StageName.IMPLEMENT, "07-review.md")


def _git_repo(path: Path) -> Path:
    path.mkdir(parents=True)
    for args in (["init"], ["config", "user.email", "t@e.com"], ["config", "user.name", "T"],
                 ["commit", "--allow-empty", "-m", "init"]):
        subprocess.run(["git", *args], cwd=path, check=True, capture_output=True)
    return path


def _implement_prompt(tmp_path: Path, fix_feedback: str | None, **config: Any) -> str:
    state_base = tmp_path / "state"
    cfg = replace(default_config(), repo_path=_git_repo(tmp_path / "repo"),
                  state_base=state_base, worktree_base=state_base / "worktrees",
                  kb_path=tmp_path / "kb", skills_base=tmp_path / "skills", **config)
    state_dir = state_base / "PROJ-1"
    state_dir.mkdir(parents=True)
    prompts: list[str] = []

    def fake(stage: Any, sandbox: Any, prompt: str, **_: Any) -> ClaudeResult:
        prompts.append(prompt)
        return ClaudeResult(0, "", "", None)

    state = TicketState("PROJ-1", fix_feedback=fix_feedback)
    with patch("claude_workflow.stages.base.run_claude_headless", side_effect=fake):
        ImplementStage().run(StageContext("PROJ-1", cfg, state, state_dir))
    return prompts[0]


def test_implement_prompt_mentions_feedback_only_when_set(tmp_path: Path) -> None:
    with_feedback = _implement_prompt(tmp_path / "a", "06-verify.md")
    without = _implement_prompt(tmp_path / "b", None)

    assert "Fix the problems listed in" in with_feedback
    assert "06-verify.md" in with_feedback
    assert "Fix the problems" not in without
    assert "07-review.md" not in without


def test_verify_failure_returns_needs_fix_and_sets_verified_diff(tmp_path: Path) -> None:
    worktree = tmp_path / "worktree"
    worktree.mkdir()
    cfg = replace(default_config(), verify_commands=("false",))
    state = TicketState("PROJ-1", worktree_path=worktree, base_commit="base")
    ctx = StageContext("PROJ-1", cfg, state, tmp_path)
    failed = subprocess.CompletedProcess[str]([], 1, "", "boom")

    with (
        patch("claude_workflow.stages.verify.capture_diff", return_value="patch"),
        patch("claude_workflow.stages.verify.subprocess.run", return_value=failed),
    ):
        result = VerifyStage().run(ctx)

    assert result.outcome is StageOutcome.NEEDS_FIX
    assert state.verified_diff is not None


def test_implement_prompt_is_test_first_with_commands(tmp_path: Path) -> None:
    prompt = _implement_prompt(tmp_path, None, verify_commands=("vendor/bin/phpunit",))

    assert "test-first" in prompt
    assert "vendor/bin/phpunit" in prompt


def test_implement_prompt_without_commands_has_no_command_list(tmp_path: Path) -> None:
    prompt = _implement_prompt(tmp_path, None)

    assert "test-first" in prompt
    assert "Check commands" not in prompt


def _verify_ctx(tmp_path: Path, **config: Any) -> StageContext:
    worktree = tmp_path / "worktree"
    worktree.mkdir()
    cfg = replace(default_config(), verify_commands=("phpunit",), **config)
    state = TicketState("PROJ-1", worktree_path=worktree, base_commit="base")
    return StageContext("PROJ-1", cfg, state, tmp_path)


def test_verify_command_timeout_is_failure(tmp_path: Path) -> None:
    ctx = _verify_ctx(tmp_path, verify_timeout=7)

    with (
        patch("claude_workflow.stages.verify.capture_diff", return_value="patch"),
        patch(
            "claude_workflow.stages.verify.subprocess.run",
            side_effect=subprocess.TimeoutExpired(["phpunit"], 7),
        ),
    ):
        result = VerifyStage().run(ctx)

    assert result.outcome is StageOutcome.NEEDS_FIX
    assert "FAIL (timeout after 7s)" in (tmp_path / "06-verify.md").read_text()


def test_verify_diff_change_lists_paths(tmp_path: Path) -> None:
    ctx = _verify_ctx(tmp_path)
    before = "diff --git a/a.php b/a.php\n+x\n"
    after = before + "diff --git a/coverage.xml b/coverage.xml\n+y\n"
    passed = subprocess.CompletedProcess[str]([], 0, "", "")

    with (
        patch("claude_workflow.stages.verify.capture_diff", side_effect=[before, after]),
        patch("claude_workflow.stages.verify.subprocess.run", return_value=passed),
    ):
        result = VerifyStage().run(ctx)

    assert result.outcome is StageOutcome.FAILED
    assert "coverage.xml" in result.message
    assert ".gitignore" in result.message
