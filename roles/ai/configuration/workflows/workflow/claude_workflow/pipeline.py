"""Pipeline orchestrator: checkpoints, approval gates, escalations, and retries."""

from __future__ import annotations

import fcntl
import re
import subprocess
import uuid
from collections.abc import Mapping
from pathlib import Path

from claude_workflow.claude_runner import run_claude_interactive
from claude_workflow.config import STAGE_ORDER, StageName, WorkflowConfig
from claude_workflow.git_host import capture_diff, commit_stage, diff_digest, is_dirty
from claude_workflow.sandbox import sandbox_paths
from claude_workflow.stages import STAGE_REGISTRY, StageOutcome, StageProtocol
from claude_workflow.stages.base import (
    StageContext,
    StageResult,
    artifact_stamp,
    blocked_questions_path,
    build_stage_sandbox,
    read_artifact,
)
from claude_workflow.state import (
    TicketState,
    load_state,
    next_stage_to_run,
    save_state,
)


def _notify(title: str, body: str) -> None:
    """Send a desktop notification via notify-send if available."""
    try:
        subprocess.run(["notify-send", title, body], check=False)
    except OSError:
        pass


def _prompt_gate(stage: StageName) -> str:
    """Prompt the user at a --step approval gate."""
    while True:
        choice = input(f"[{stage.value}] [c]ontinue / [r]etry stage / [a]bort: ").strip().lower()
        if choice in {"c", "continue"}:
            return "c"
        if choice in {"r", "retry"}:
            return "r"
        if choice in {"a", "abort"}:
            return "a"


def _run_escalation_qa(ctx: StageContext, blocked_stage: StageName) -> bool:
    """Run a short interactive Q&A turn for blocked-questions.md and clear the blocker."""
    bq_path = blocked_questions_path(ctx.state_dir)
    questions = read_artifact(bq_path)
    answers_path = ctx.state_dir / "03-qa.md"
    previous_answers = read_artifact(answers_path)
    if not questions.strip():
        return False

    _notify(
        f"claude-workflow: {ctx.ticket_id}",
        f"{blocked_stage.value} needs human input (blocked-questions.md)",
    )

    sandbox = build_stage_sandbox(
        ctx,
        StageName.QA,
        repo_dir=ctx.config.repo_path,
        kb_dir=ctx.config.kb_path,
        workdir=ctx.config.repo_path,
    )
    paths = sandbox_paths(sandbox)
    prompt = (
        f"Stage '{blocked_stage.value}' is blocked on these questions:\n\n{questions}\n\n"
        f"Ask the user these questions, append the answers to {paths.notes_dir / '03-qa.md'}, "
        "and leave the blocker file in place for the host to clear."
    )
    rc = run_claude_interactive(
        ctx.config.stages[StageName.QA],
        sandbox,
        prompt,
        session_id=str(uuid.uuid4()),
        resume=False,
    )
    if rc != 0 or artifact_stamp(answers_path) is None:
        return False
    answers = read_artifact(answers_path)
    if not answers.startswith(previous_answers) or not answers[len(previous_answers):].strip():
        return False
    return True


def _mark_completed(state: TicketState, stage: StageName) -> None:
    if stage not in state.completed_stages:
        state.completed_stages.append(stage)
    state.current_stage = None
    state.approval_pending = False


def _finalize(state: TicketState, ticket_id: str) -> None:
    worktree = state.worktree_path
    if worktree is None or not state.base_commit:
        raise ValueError("Completing Retro requires a ticket worktree.")
    if diff_digest(capture_diff(worktree, state.base_commit)) != state.verified_diff:
        raise ValueError("Worktree changed after review. Restart from Verify.")
    if commit_stage(worktree, f"{ticket_id}: implement plan"):
        if is_dirty(worktree):
            raise ValueError("Worktree is dirty after commit. Inspect it and restart from Verify.")
        if diff_digest(capture_diff(worktree, state.base_commit)) != state.verified_diff:
            raise ValueError("Commit changed the verified diff. Inspect it and restart from Verify.")


def run_pipeline(
    ticket_id: str,
    config: WorkflowConfig,
    from_stage: StageName | None = None,
    auto: bool = False,
    stage_runners: Mapping[StageName, StageProtocol] | None = None,
    *,
    only_stage: StageName | None = None,
) -> int:
    """Run the 8-stage pipeline for ticket_id from the appropriate starting stage."""
    if re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*-[0-9]+", ticket_id) is None:
        print("Error: expected a Jira ticket key such as PROJ-123.")
        return 1

    state_dir = config.state_base / ticket_id
    try:
        state_dir.mkdir(parents=True, exist_ok=True)
        with (state_dir / ".lock").open("a") as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                print(f"Error: another workflow is running for {ticket_id}.")
                return 1
            return _run_pipeline(
                ticket_id, config, only_stage or from_stage, auto, stage_runners, state_dir,
                single_stage=only_stage is not None,
            )
    except (OSError, RuntimeError, ValueError, EOFError) as exc:
        print(f"Error running {ticket_id}: {exc}")
        return 1
    except KeyboardInterrupt:
        print(f"Interrupted workflow for {ticket_id}.")
        return 130


def _run_pipeline(
    ticket_id: str,
    config: WorkflowConfig,
    from_stage: StageName | None,
    auto: bool,
    stage_runners: Mapping[StageName, StageProtocol] | None,
    state_dir: Path,
    *,
    single_stage: bool,
) -> int:
    runners = stage_runners if stage_runners is not None else STAGE_REGISTRY
    state = load_state(state_dir, ticket_id)
    if state.ticket_id != ticket_id:
        raise ValueError("Checkpoint ticket does not match the requested ticket.")
    repo_path = config.repo_path.resolve()
    if state.repo_path is not None and state.repo_path != repo_path:
        raise ValueError("Checkpoint belongs to another repository. Use a separate state directory.")
    if stage_runners is None and state.worktree_path is not None:
        expected_worktree = (config.worktree_base / ticket_id).resolve()
        if state.worktree_path.resolve() != expected_worktree:
            raise ValueError("Checkpoint worktree is outside the configured ticket worktree path.")
    state.repo_path = repo_path

    start_stage = next_stage_to_run(state, from_stage)
    if start_stage is None:
        print(f"All stages already completed for {ticket_id}.")
        return 0

    idx = STAGE_ORDER.index(start_stage)
    if from_stage is not None:
        downstream = STAGE_ORDER[idx:]
        if stage_runners is None:
            missing = [s.value for s in STAGE_ORDER[:idx] if s not in state.completed_stages]
            if missing:
                raise ValueError(f"Complete prerequisite stages first: {', '.join(missing)}")
        state.completed_stages = [s for s in state.completed_stages if s not in downstream]
        for stage in downstream:
            state.session_ids.pop(stage.value, None)
            state.escalation_counts.pop(stage.value, None)
        if StageName.VERIFY in downstream:
            state.verified_diff = None
        state.approval_pending = False

    while idx < len(STAGE_ORDER):
        stage = STAGE_ORDER[idx]
        if state.approval_pending:
            action = "c" if auto else _prompt_gate(stage)
            if action == "a":
                print(f"Aborted after {stage.value}.")
                return 1
            if action == "c":
                if stage is StageName.RETRO and stage_runners is None:
                    _finalize(state, ticket_id)
                _mark_completed(state, stage)
                save_state(state_dir, state)
                if single_stage:
                    return 0
                idx += 1
                continue
            state.approval_pending = False
            state.session_ids.pop(stage.value, None)
            state.escalation_counts.pop(stage.value, None)

        state.current_stage = stage
        save_state(state_dir, state)

        ctx = StageContext(
            ticket_id=ticket_id,
            config=config,
            state=state,
            state_dir=state_dir,
        )
        blocker = blocked_questions_path(state_dir)
        if stage in {StageName.PLAN, StageName.IMPLEMENT} and artifact_stamp(blocker):
            result = StageResult(StageOutcome.BLOCKED_QUESTIONS, blocker, "Pending clarification")
        else:
            result = runners[stage].run(ctx)

        if result.outcome is StageOutcome.BLOCKED_QUESTIONS:
            count = state.escalation_counts.get(stage.value, 0)
            if count >= config.max_escalations:
                print(
                    f"Error: {stage.value} exceeded max_escalations ({config.max_escalations})."
                )
                return 1
            if not _run_escalation_qa(ctx, stage):
                print(f"Error: escalation Q&A failed for {stage.value}.")
                return 1
            state.escalation_counts[stage.value] = count + 1
            save_state(state_dir, state)
            blocker.unlink(missing_ok=True)
            continue

        if result.outcome is StageOutcome.FAILED:
            print(f"Stage {stage.value} failed: {result.message}")
            return 1

        state.approval_pending = True
        save_state(state_dir, state)

    return 0
