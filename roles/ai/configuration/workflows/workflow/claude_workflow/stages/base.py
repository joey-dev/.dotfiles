"""Shared stage types, sandbox helpers, and artifact utilities."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Literal, Protocol

from claude_workflow.claude_runner import run_claude_headless
from claude_workflow.config import StageConfig, StageName, WorkflowConfig
from claude_workflow.deps import resolve_shared_dependencies
from claude_workflow.git_host import ensure_worktree, is_dirty, rev_parse_head
from claude_workflow.sandbox import SandboxSpec
from claude_workflow.state import TicketState, save_state


class StageOutcome(str, Enum):
    """Result status returned by a pipeline stage."""

    DONE = "done"
    BLOCKED_QUESTIONS = "blocked_questions"
    # Verify or Review found problems that Implement should fix.
    NEEDS_FIX = "needs_fix"
    # Verify could not run the Docker tests safely; the human continues, retries or aborts.
    NEEDS_HUMAN = "needs_human"
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


def ensure_ticket_worktree(ctx: StageContext) -> Path:
    """Create or reuse the ticket worktree, and remember it in the ticket state.

    The base commit is fixed the first time, so later stages see the same code
    even if the main checkout moves on.
    """
    state = ctx.state
    repo = ctx.config.repo_path
    branch_name = state.branch_name or ctx.ticket_id.lower()
    worktree_path = state.worktree_path or (ctx.config.worktree_base / ctx.ticket_id)
    first_time = state.worktree_path is None
    base_commit = state.base_commit or rev_parse_head(repo)

    if first_time and is_dirty(repo):
        print(f"Warning: uncommitted changes in {repo} are not part of the ticket worktree.")

    ensure_worktree(repo, worktree_path, branch_name, base_ref=base_commit)
    if first_time and is_dirty(worktree_path):
        raise RuntimeError(f"Existing worktree has unowned changes: {worktree_path}")

    if (state.worktree_path, state.branch_name, state.base_commit) != (
        worktree_path,
        branch_name,
        base_commit,
    ):
        state.worktree_path = worktree_path
        state.branch_name = branch_name
        state.base_commit = base_commit
        save_state(ctx.state_dir, state)
    return worktree_path


def stage_skills(config: WorkflowConfig, stage: StageName) -> tuple[Path, ...]:
    """Return only shared/ and <stage>/ skill directories for least-privilege mounting."""
    return (
        config.skills_base / "shared",
        config.skills_base / stage.value,
    )


def stage_cache_dir(config: WorkflowConfig, ticket: str, stage: StageName) -> Path:
    """Create and return the stage's cache folder (bound at /tmp/cw-cache, used as $TMPDIR).

    It lives outside the ticket's notes folder, so one stage cannot write another's cache.
    """
    cache = config.state_base / ".cache" / ticket / stage.value
    cache.mkdir(parents=True, exist_ok=True)
    return cache


def _home_ro_mounts(config: WorkflowConfig, stage: StageName) -> tuple[tuple[Path, str], ...]:
    """Read-only extras in the sandbox $HOME: your CLAUDE.md, and all skills for Retro."""
    mounts: list[tuple[Path, str]] = []
    claude_md = Path.home() / ".claude" / "CLAUDE.md"
    if claude_md.is_file():
        mounts.append((claude_md, ".claude/CLAUDE.md"))
    if stage is StageName.RETRO:
        # Retro proposes skill changes, so it may read every skill.
        mounts.append((config.skills_base, "skills"))
    return tuple(mounts)


def _repo_mcp_config(config: WorkflowConfig, stage_cfg: StageConfig) -> Path | None:
    """A stage that uses MCP tools gets the repo's own .mcp.json, if it has one."""
    if not any(tool.startswith("mcp__") for tool in stage_cfg.allowed_tools):
        return None
    candidate = config.repo_path / ".mcp.json"
    return candidate if candidate.is_file() else None


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
    if stage_cfg.mcp_config is not None and not stage_cfg.mcp_config.is_file():
        raise ValueError(f"{stage.value} MCP config does not exist: {stage_cfg.mcp_config}")
    flake = ctx.config.flake_path if stage in {StageName.IMPLEMENT, StageName.VERIFY} else None
    if flake is not None and not flake.exists():
        raise ValueError(f"Configured Nix flake does not exist: {flake}")
    home_mounts = _home_ro_mounts(ctx.config, stage)
    overlays: tuple[tuple[Path, str], ...] = ()
    if repo_dir is not None and repo_dir == ctx.state.worktree_path:
        overlays = resolve_shared_dependencies(
            ctx.config.repo_path, repo_dir, ctx.config.shared_dependencies
        )
    # Host copies (e.g. certificates) are copied into the worktree for Docker; hide them.
    docker = ctx.config.docker
    masks = docker.host_copies if docker is not None and repo_dir is not None else ()
    cache = (
        stage_cache_dir(ctx.config, ctx.ticket_id, stage)
        if stage in {StageName.IMPLEMENT, StageName.VERIFY}
        else None
    )
    return SandboxSpec(
        repo_dir=repo_dir,
        repo_access=stage_cfg.repo_access,
        state_dir=ctx.state_dir,
        skills_dirs=stage_skills(ctx.config, stage),
        kb_dir=kb_dir,
        allow_network=stage_cfg.allow_network,
        workdir=workdir,
        mcp_config=stage_cfg.mcp_config or _repo_mcp_config(ctx.config, stage_cfg),
        flake_dir=flake,
        repo_ro_overlays=overlays,
        home_ro_mounts=home_mounts,
        cache_dir=cache,
        repo_masks=masks,
    )


def blocked_questions_path(state_dir: Path) -> Path:
    """Return the path where Plan/Implement write escalation questions."""
    return state_dir / "blocked-questions.md"


Verdict = Literal["APPROVED", "CHANGES_REQUESTED"]
# Optional "Verdict:", the verdict (maybe in **bold**), then nothing or ":"/"—" + details.
_VERDICT_LINE = re.compile(
    r"(?:VERDICT\s*:\s*)?[*_`]*(APPROVED|CHANGES[ _]REQUESTED)[*_`]*\s*(?:[:—–-].*)?"
)


def parse_verdict(text: str) -> Verdict | None:
    """Read APPROVED or CHANGES_REQUESTED from the first non-empty line.

    Markdown around it is fine: "# APPROVED", "**Approved**", "Changes requested: x".
    Anything else after the verdict ("APPROVED WITH CHANGES") is not a verdict.
    """
    first_line = next((line for line in text.splitlines() if line.strip()), "")
    cleaned = first_line.strip().strip("#*_`> ").rstrip(".!").upper()
    match = _VERDICT_LINE.fullmatch(cleaned)
    if match is None:
        return None
    return "APPROVED" if match.group(1) == "APPROVED" else "CHANGES_REQUESTED"


def has_blocker(state_dir: Path) -> bool:
    """True if blocked-questions.md contains questions.

    An empty blocker file is deleted, so it can never block the ticket forever.
    """
    blocker = blocked_questions_path(state_dir)
    if artifact_stamp(blocker) is None:
        return False
    if read_artifact(blocker).strip():
        return True
    blocker.unlink()
    return False


def blocked_result(stage: StageName, state_dir: Path) -> StageResult:
    """The result for a stage that asked the human a question."""
    return StageResult(
        outcome=StageOutcome.BLOCKED_QUESTIONS,
        artifact_path=blocked_questions_path(state_dir),
        message=f"{stage.value} requested human clarification via blocked-questions.md",
    )


def read_artifact(path: Path) -> str:
    """Read a UTF-8 artifact if it exists, otherwise return an empty string."""
    if not path.is_symlink() and path.is_file():
        return path.read_text(encoding="utf-8")
    return ""


def write_artifact(path: Path, content: str) -> None:
    """Replace a host-generated artifact without following its previous path."""
    with NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, delete=False
    ) as output:
        temporary = Path(output.name)
        try:
            output.write(content)
            output.flush()
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)


def artifact_stamp(path: Path) -> tuple[int, int, int] | None:
    """Identify a regular artifact and the last filesystem change to it."""
    if path.is_symlink() or not path.is_file():
        return None
    info = path.stat()
    return info.st_ino, info.st_mtime_ns, info.st_ctime_ns


def artifact_result(
    stage: StageName,
    path: Path,
    previous: tuple[int, int, int] | None = None,
) -> StageResult:
    stamp = artifact_stamp(path)
    if stamp is None or stamp == previous or not read_artifact(path).strip():
        return StageResult(
            StageOutcome.FAILED, None, f"{stage.value} did not write a fresh {path.name}"
        )
    return StageResult(StageOutcome.DONE, path, f"{stage.value} completed")


def run_headless_with_escalation(
    ctx: StageContext,
    stage: StageName,
    sandbox: SandboxSpec,
    prompt: str,
    artifact_path: Path,
) -> StageResult:
    """Run a headless Claude stage and check for blocked-questions.md or failure."""
    stage_cfg = ctx.config.stages[stage]
    previous = artifact_stamp(artifact_path)
    result = run_claude_headless(
        stage_cfg, sandbox, prompt, timeout=ctx.config.headless_timeout
    )
    if stage in {StageName.PLAN, StageName.IMPLEMENT} and has_blocker(ctx.state_dir):
        return blocked_result(stage, ctx.state_dir)
    if result.returncode != 0:
        detail = result.stderr.strip() or f"exit code {result.returncode}"
        return StageResult(
            outcome=StageOutcome.FAILED,
            artifact_path=None,
            message=f"{stage.value} failed: {detail}",
        )
    return artifact_result(stage, artifact_path, previous)
