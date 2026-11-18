"""Crash-safe per-ticket state persistence and resume logic."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from claude_workflow.config import STAGE_ORDER, StageName


@dataclass
class TicketState:
    """Persisted execution state for a single Jira ticket."""

    ticket_id: str
    current_stage: StageName | None = None
    completed_stages: list[StageName] = field(default_factory=list)
    session_ids: dict[str, str] = field(default_factory=dict)
    worktree_path: Path | None = None
    branch_name: str = ""
    base_commit: str = ""
    escalation_counts: dict[str, int] = field(default_factory=dict)
    approval_pending: bool = False
    repo_path: Path | None = None
    verified_diff: str | None = None
    # How often Verify/Review sent the ticket back to Implement.
    fix_rounds: int = 0
    # Artifact (e.g. "07-review.md") with the problems Implement must fix next.
    fix_feedback: str | None = None


def _state_file(state_dir: Path) -> Path:
    return state_dir / "state.json"


def load_state(state_dir: Path, ticket_id: str) -> TicketState:
    """Load TicketState from state.json, or return a fresh state if absent."""
    path = _state_file(state_dir)
    if not path.is_file():
        return TicketState(ticket_id=ticket_id)

    raw: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    current_raw = raw.get("current_stage")
    current_stage = StageName(current_raw) if current_raw is not None else None
    completed = [StageName(item) for item in raw.get("completed_stages", [])]
    session_ids = {str(k): str(v) for k, v in raw.get("session_ids", {}).items()}
    wt_raw = raw.get("worktree_path")
    repo_raw = raw.get("repo_path")
    worktree_path = Path(wt_raw) if wt_raw is not None else None
    escalation_counts = {
        str(k): int(v) for k, v in raw.get("escalation_counts", {}).items()
    }

    return TicketState(
        ticket_id=str(raw.get("ticket_id", ticket_id)),
        current_stage=current_stage,
        completed_stages=completed,
        session_ids=session_ids,
        worktree_path=worktree_path,
        branch_name=str(raw.get("branch_name", "")),
        base_commit=str(raw.get("base_commit", "")),
        escalation_counts=escalation_counts,
        approval_pending=bool(raw.get("approval_pending", False)),
        repo_path=Path(repo_raw) if repo_raw is not None else None,
        verified_diff=raw.get("verified_diff"),
        fix_rounds=int(raw.get("fix_rounds", 0)),
        fix_feedback=raw.get("fix_feedback"),
    )


def save_state(state_dir: Path, state: TicketState) -> None:
    """Persist TicketState atomically via a temporary file and os.replace."""
    state_dir.mkdir(parents=True, exist_ok=True)
    target = _state_file(state_dir)

    payload: dict[str, Any] = {
        "ticket_id": state.ticket_id,
        "current_stage": state.current_stage.value if state.current_stage is not None else None,
        "completed_stages": [s.value for s in state.completed_stages],
        "session_ids": state.session_ids,
        "worktree_path": str(state.worktree_path) if state.worktree_path is not None else None,
        "branch_name": state.branch_name,
        "base_commit": state.base_commit,
        "escalation_counts": state.escalation_counts,
        "approval_pending": state.approval_pending,
        "repo_path": str(state.repo_path) if state.repo_path is not None else None,
        "verified_diff": state.verified_diff,
        "fix_rounds": state.fix_rounds,
        "fix_feedback": state.fix_feedback,
    }

    with NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=state_dir, prefix=".checkpoint-", delete=False
    ) as checkpoint:
        tmp_path = Path(checkpoint.name)
        try:
            checkpoint.write(json.dumps(payload, indent=2) + "\n")
            checkpoint.flush()
            os.fsync(checkpoint.fileno())
            os.replace(tmp_path, target)
        finally:
            tmp_path.unlink(missing_ok=True)
    directory = os.open(state_dir, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def next_stage_to_run(
    state: TicketState,
    from_stage: StageName | None,
) -> StageName | None:
    """Determine the next stage to run, honoring --from-stage and crash resume."""
    if from_stage is not None:
        return from_stage
    if state.current_stage is not None:
        return state.current_stage
    completed_set = set(state.completed_stages)
    for stage in STAGE_ORDER:
        if stage not in completed_set:
            return stage
    return None
