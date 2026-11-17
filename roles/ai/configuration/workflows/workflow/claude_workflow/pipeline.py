"""Pipeline orchestrator: checkpoints, approval gates, escalations, and retries."""

from __future__ import annotations

import subprocess
import uuid
from collections.abc import Mapping

from claude_workflow.claude_runner import run_claude_interactive
from claude_workflow.config import STAGE_ORDER, StageName, WorkflowConfig
from claude_workflow.sandbox import sandbox_paths
from claude_workflow.stages import STAGE_REGISTRY, StageOutcome, StageProtocol
from claude_workflow.stages.base import (
    StageContext,
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
        f"and remove {paths.notes_dir / 'blocked-questions.md'}."
    )
    rc = run_claude_interactive(
        ctx.config.stages[StageName.QA],
        sandbox,
        prompt,
        session_id=str(uuid.uuid4()),
        resume=False,
    )
    if rc != 0:
        return False
    if bq_path.exists():
        bq_path.unlink()
    return True


def _mark_completed(state: TicketState, stage: StageName) -> None:
    if stage not in state.completed_stages:
        state.completed_stages.append(stage)
    state.current_stage = None


def run_pipeline(
    ticket_id: str,
    config: WorkflowConfig,
    from_stage: StageName | None = None,
    auto: bool = False,
    stage_runners: Mapping[StageName, StageProtocol] | None = None,
) -> int:
    """Run the 8-stage pipeline for ticket_id from the appropriate starting stage."""
    runners = stage_runners if stage_runners is not None else STAGE_REGISTRY
    state_dir = config.state_base / ticket_id
    state = load_state(state_dir, ticket_id)

    start_stage = next_stage_to_run(state, from_stage)
    if start_stage is None:
        print(f"All stages already completed for {ticket_id}.")
        return 0

    idx = STAGE_ORDER.index(start_stage)
    while idx < len(STAGE_ORDER):
        stage = STAGE_ORDER[idx]
        state.current_stage = stage
        save_state(state_dir, state)

        ctx = StageContext(
            ticket_id=ticket_id,
            config=config,
            state=state,
            state_dir=state_dir,
        )
        result = runners[stage].run(ctx)

        if result.outcome is StageOutcome.BLOCKED_QUESTIONS:
            count = state.escalation_counts.get(stage.value, 0)
            if count >= config.max_escalations:
                print(
                    f"Error: {stage.value} exceeded max_escalations ({config.max_escalations})."
                )
                return 1
            state.escalation_counts[stage.value] = count + 1
            save_state(state_dir, state)
            if not _run_escalation_qa(ctx, stage):
                print(f"Error: escalation Q&A failed for {stage.value}.")
                return 1
            continue

        if result.outcome is StageOutcome.FAILED:
            print(f"Stage {stage.value} failed: {result.message}")
            return 1

        _mark_completed(state, stage)
        save_state(state_dir, state)

        if not auto:
            action = _prompt_gate(stage)
            if action == "r":
                if stage in state.completed_stages:
                    state.completed_stages.remove(stage)
                state.current_stage = stage
                save_state(state_dir, state)
                continue
            if action == "a":
                print(f"Aborted after {stage.value}.")
                return 1

        idx += 1

    return 0
