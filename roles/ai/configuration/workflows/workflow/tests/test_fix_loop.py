"""Verify and Review can send the ticket back to Implement, a limited number of times."""

from __future__ import annotations

import subprocess
from dataclasses import replace
from pathlib import Path
from typing import Any
from unittest.mock import patch

from claude_workflow.claude_runner import ClaudeResult
from claude_workflow.commands import Command, Parameter, VerifyEntry
from claude_workflow.config import STAGE_ORDER, StageName, WorkflowConfig, default_config
from claude_workflow.pipeline import run_pipeline
from claude_workflow.stages.base import (
    StageContext,
    StageOutcome,
    StageProtocol,
    StageResult,
)
from claude_workflow.stages.implement import ImplementStage
from claude_workflow.stages.review import ReviewStage
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


def _cmd(name: str, **overrides: Any) -> Command:
    fields: dict[str, Any] = {
        "name": name, "description": "", "run_in": "sandbox", "command": "true",
        "working_directory": None, "timeout": 60, "needs_compose_stack": False,
        "needs_git": False, "container": None, "user": None,
    }
    fields.update(overrides)
    return Command(**fields)


_PHPUNIT = _cmd(
    "phpunit",
    description="PHP unit tests.",
    working_directory="legacy",
    command="vendor/bin/phpunit {{filter}} --config=phpunit.xml.dist",
    parameters={"filter": Parameter(
        description="Only matching tests.", format="--filter {{value}}",
        pattern="[A-Za-z0-9_]+", example="InvoiceTest",
    )},
)
_API = _cmd(
    "tests:api",
    description="API suite.",
    run_in="host",
    needs_compose_stack=True,
    command="./test_runner.sh api {{filter}}",
    parameters={"filter": Parameter(required=True, pattern="[A-Za-z.]+", example="FooCest.php")},
)


def test_implement_prompt_is_test_first_with_catalogue(tmp_path: Path) -> None:
    prompt = _implement_prompt(
        tmp_path, None, commands={"phpunit": _PHPUNIT, "tests:api": _API},
        verify=(VerifyEntry("phpunit"),),
    )

    assert "test-first" in prompt
    assert "`phpunit`" in prompt and "`tests:api`" in prompt
    assert "PHP unit tests." in prompt
    # sandbox commands show the line to run yourself, host commands don't
    assert "`vendor/bin/phpunit --filter InvoiceTest --config=phpunit.xml.dist`" in prompt
    assert "./test_runner.sh" not in prompt
    assert "only in Verify" in prompt
    assert "Verify always runs: `phpunit`" in prompt


def test_implement_prompt_without_commands_has_no_command_list(tmp_path: Path) -> None:
    prompt = _implement_prompt(tmp_path, None)

    assert "test-first" in prompt
    assert "Verify always runs" not in prompt


def test_implement_prompt_points_to_tests_file(tmp_path: Path) -> None:
    prompt = _implement_prompt(tmp_path, None)

    assert "tests.txt" in prompt
    assert "flake:" not in prompt
    assert "docker:" not in prompt
    assert "Verify" in prompt

def _review_ctx(tmp_path: Path, tests: str | None) -> StageContext:
    worktree = tmp_path / "worktree"
    worktree.mkdir()
    if tests is not None:
        (tmp_path / "tests.txt").write_text(tests)
    cfg = replace(default_config(), state_base=tmp_path / "state-base",
                  kb_path=tmp_path / "kb", skills_base=tmp_path / "skills")
    state = TicketState("PROJ-1", worktree_path=worktree, base_commit="base", verified_diff="d")
    return StageContext("PROJ-1", cfg, state, tmp_path)


def _run_review(ctx: StageContext, append_to_tests: str | None) -> tuple[StageResult, list[str]]:
    prompts: list[str] = []

    def fake(stage: Any, sandbox: Any, prompt: str, **_: Any) -> ClaudeResult:
        prompts.append(prompt)
        lens = "correctness" if "logic bugs" in prompt else "conventions"
        (ctx.state_dir / f"07-review-{lens}.md").write_text("APPROVED\n")
        if lens == "correctness" and append_to_tests is not None:
            with (ctx.state_dir / "tests.txt").open("a") as handle:
                handle.write(append_to_tests)
        return ClaudeResult(0, "", "", None)

    with (
        patch("claude_workflow.stages.review.capture_diff", return_value="patch"),
        patch("claude_workflow.stages.review.diff_digest", return_value="d"),
        patch("claude_workflow.stages.review.run_claude_headless", side_effect=fake),
    ):
        return ReviewStage().run(ctx), prompts


def test_review_test_suggestion_forces_fix_round(tmp_path: Path) -> None:
    ctx = _review_ctx(tmp_path, "phpunit\n")

    result, prompts = _run_review(ctx, "# suggested by review\nphpunit filter=Foo\n")

    assert "# suggested by review" in prompts[0]
    assert "tests.txt" in prompts[0]
    assert result.outcome is StageOutcome.NEEDS_FIX
    assert result.message == "Review suggested tests in tests.txt"


def test_review_unchanged_tests_file_is_done(tmp_path: Path) -> None:
    result, _ = _run_review(_review_ctx(tmp_path, "phpunit\n"), None)

    assert result.outcome is StageOutcome.DONE


def test_review_missing_tests_file_is_unchanged(tmp_path: Path) -> None:
    result, _ = _run_review(_review_ctx(tmp_path, None), None)

    assert result.outcome is StageOutcome.DONE


def test_review_correctness_prompt_has_catalogue(tmp_path: Path) -> None:
    ctx = _review_ctx(tmp_path, "phpunit\n")
    ctx = replace(ctx, config=replace(ctx.config, commands={"phpunit": _PHPUNIT}))

    _, prompts = _run_review(ctx, None)

    correctness = next(p for p in prompts if "logic bugs" in p)
    assert "`phpunit filter=InvoiceTest`" in correctness
    assert "<command-name>" in correctness


def _human_setup(tmp_path: Path) -> tuple[WorkflowConfig, list[Any], dict[StageName, Any]]:
    cfg, log, runners = _setup(tmp_path, [])
    runners[StageName.VERIFY] = _Scripted(log, StageName.VERIFY, [StageOutcome.NEEDS_HUMAN])
    _completed_until(cfg, "PROJ-1", StageName.VERIFY)
    return cfg, log, runners


def test_docker_stop_continue_goes_on_to_review(tmp_path: Path) -> None:
    cfg, log, runners = _human_setup(tmp_path)

    with patch("builtins.input", side_effect=["c", "c", "c", "c"]):
        assert run_pipeline("PROJ-1", cfg, stage_runners=runners) == 0

    assert _names(log) == [StageName.VERIFY, StageName.REVIEW, StageName.RETRO]
    state = load_state(tmp_path / "PROJ-1", "PROJ-1")
    assert StageName.VERIFY in state.completed_stages
    assert state.fix_rounds == 0


def test_docker_stop_retry_reruns_verify(tmp_path: Path) -> None:
    cfg, log, runners = _human_setup(tmp_path)

    with patch("builtins.input", side_effect=["r", "c", "c", "c"]):
        assert run_pipeline("PROJ-1", cfg, stage_runners=runners) == 0

    assert _names(log)[:3] == [StageName.VERIFY, StageName.VERIFY, StageName.REVIEW]


def test_docker_stop_abort_exits_1(tmp_path: Path) -> None:
    cfg, log, runners = _human_setup(tmp_path)

    with patch("builtins.input", side_effect=["a"]):
        assert run_pipeline("PROJ-1", cfg, stage_runners=runners) == 1

    assert _names(log) == [StageName.VERIFY]
    assert StageName.VERIFY not in load_state(tmp_path / "PROJ-1", "PROJ-1").completed_stages


def test_docker_stop_in_auto_mode_stops_with_hint(tmp_path: Path, capsys: Any) -> None:
    cfg, log, runners = _human_setup(tmp_path)

    with patch("builtins.input", side_effect=AssertionError("no prompt in --auto")):
        assert run_pipeline("PROJ-1", cfg, auto=True, stage_runners=runners) == 1

    assert _names(log) == [StageName.VERIFY]
    assert "without --auto" in capsys.readouterr().out

