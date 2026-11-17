"""Shared stage types, sandbox helpers, and artifact utilities."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Protocol

from claude_workflow.claude_runner import run_claude_headless
from claude_workflow.config import StageName, WorkflowConfig
from claude_workflow.sandbox import SandboxPaths, SandboxSpec, sandbox_paths
from claude_workflow.state import TicketState


class StageOutcome(str, Enum):
    """Result status returned by a pipeline stage."""

    DONE = "done"
    BLOCKED_QUESTIONS = "blocked_questions"
    FAILED = "failed"


@dataclass(frozen=True)
class StageContext:
    """Execution context passed to every stage."""

    ticket_id: str
    config: WorkflowConfig
    state: TicketState
    state_dir: Path


@dataclass(frozen=True)
class StageResult:
    """Outcome and primary artifact produced by a stage."""

    outcome: StageOutcome
    artifact_path: Path | None
    message: str


class StageProtocol(Protocol):
    """Protocol implemented by every stage module."""

    def run(self, ctx: StageContext) -> StageResult:
        """Execute the stage and return its outcome."""
        ...


def stage_skills(config: WorkflowConfig, stage: StageName) -> tuple[Path, ...]:
    """Return only shared/ and <stage>/ skill directories for least-privilege mounting."""
    return (
        config.skills_base / "shared",
        config.skills_base / stage.value,
    )


def build_stage_sandbox(
    ctx: StageContext,
    stage: StageName,
    *,
    repo_dir: Path | None,
    kb_dir: Path | None,
    workdir: Path,
) -> SandboxSpec:
    """Construct a SandboxSpec for a stage from WorkflowConfig."""
    stage_cfg = ctx.config.stages[stage]
    return SandboxSpec(
        repo_dir=repo_dir,
        repo_access=stage_cfg.repo_access,
        state_dir=ctx.state_dir,
        skills_dirs=stage_skills(ctx.config, stage),
        kb_dir=kb_dir,
        allow_network=stage_cfg.allow_network,
        workdir=workdir,
        mcp_config=stage_cfg.mcp_config,
        flake_dir=ctx.config.flake_path,
    )


def skill_prompt_prefix(ctx: StageContext, stage: StageName, paths: SandboxPaths) -> str:
    """Return a prompt instruction pointing Claude to the mounted stage SKILL.md files."""
    if paths.skills_dir is None:
        return ""
    skill_files = [
        paths.skills_dir / skill_dir.name / "SKILL.md"
        for skill_dir in stage_skills(ctx.config, stage)
        if (skill_dir / "SKILL.md").is_file()
    ]
    if not skill_files:
        return ""
    joined = ", ".join(str(p) for p in skill_files)
    return f"First read and follow the instructions in: {joined}.\n\n"


def blocked_questions_path(state_dir: Path) -> Path:
    """Return the path where Plan/Implement write escalation questions."""
    return state_dir / "blocked-questions.md"


def read_artifact(path: Path) -> str:
    """Read a UTF-8 artifact if it exists, otherwise return an empty string."""
    if path.is_file():
        return path.read_text(encoding="utf-8")
    return ""


def run_headless_with_escalation(
    ctx: StageContext,
    stage: StageName,
    sandbox: SandboxSpec,
    prompt: str,
    artifact_path: Path,
) -> StageResult:
    """Run a headless Claude stage and check for blocked-questions.md or failure."""
    stage_cfg = ctx.config.stages[stage]
    result = run_claude_headless(stage_cfg, sandbox, prompt)
    if blocked_questions_path(ctx.state_dir).is_file():
        return StageResult(
            outcome=StageOutcome.BLOCKED_QUESTIONS,
            artifact_path=blocked_questions_path(ctx.state_dir),
            message=f"{stage.value} requested human clarification via blocked-questions.md",
        )
    if result.returncode != 0:
        detail = result.stderr.strip() or f"exit code {result.returncode}"
        return StageResult(
            outcome=StageOutcome.FAILED,
            artifact_path=None,
            message=f"{stage.value} failed: {detail}",
        )
    return StageResult(
        outcome=StageOutcome.DONE,
        artifact_path=artifact_path,
        message=f"{stage.value} completed",
    )
