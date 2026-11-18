"""Configuration models and JSON loader for claude-workflow."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, replace
from enum import Enum
from pathlib import Path
from typing import Any, cast

from claude_workflow.deps import SharedDependency


class StageName(str, Enum):
    """Ordered pipeline stage identifiers."""

    INTAKE = "intake"
    EXPLORE = "explore"
    QA = "qa"
    PLAN = "plan"
    IMPLEMENT = "implement"
    VERIFY = "verify"
    REVIEW = "review"
    RETRO = "retro"


STAGE_ORDER: tuple[StageName, ...] = (
    StageName.INTAKE,
    StageName.EXPLORE,
    StageName.QA,
    StageName.PLAN,
    StageName.IMPLEMENT,
    StageName.VERIFY,
    StageName.REVIEW,
    StageName.RETRO,
)


class RepoAccess(str, Enum):
    """Filesystem mount mode for the target repository inside bwrap."""

    NONE = "none"
    RO = "ro"
    RW = "rw"


@dataclass(frozen=True)
class StageConfig:
    """Execution settings for a single pipeline stage."""

    name: StageName
    model: str
    thinking: str
    repo_access: RepoAccess
    allow_network: bool
    mcp_config: Path | None = None
    allowed_tools: tuple[str, ...] = ()


@dataclass(frozen=True)
class WorkflowConfig:
    """Top-level configuration for the workflow orchestrator."""

    repo_path: Path
    worktree_base: Path
    state_base: Path
    kb_path: Path
    skills_base: Path
    flake_path: Path | None
    verify_commands: tuple[str, ...]
    max_plan_reviews: int
    max_escalations: int
    stages: dict[StageName, StageConfig]
    shared_dependencies: tuple[SharedDependency, ...] = ()
    max_fix_rounds: int = 3
    headless_timeout: int = 3600  # seconds per headless Claude call
    verify_timeout: int = 1800  # seconds per verify command
    commit_no_verify: bool = True  # skip git hooks for the final commit


def _default_state_base() -> Path:
    xdg_state = os.environ.get("XDG_STATE_HOME")
    base = Path(xdg_state) if xdg_state else Path.home() / ".local" / "state"
    return base / "claude-workflow"


def _default_skills_base() -> Path:
    env_skills = os.environ.get("CLAUDE_WORKFLOW_SKILLS")
    if env_skills:
        return Path(env_skills).expanduser()
    package_skills = Path(__file__).resolve().parent.parent / "skills"
    if package_skills.is_dir():
        return package_skills
    xdg_config = os.environ.get("XDG_CONFIG_HOME")
    base = Path(xdg_config) if xdg_config else Path.home() / ".config"
    return base / "claude-workflow" / "skills"


def default_stages() -> dict[StageName, StageConfig]:
    """Return the default per-stage configuration matching the design doc."""
    return {
        StageName.INTAKE: StageConfig(
            name=StageName.INTAKE,
            model="sonnet",
            thinking="medium",
            repo_access=RepoAccess.NONE,
            allow_network=True,
            # The company's Atlassian server from the repo's .mcp.json.
            allowed_tools=("Read", "Write", "mcp__Atlassian-Rovo-MCP__*"),
        ),
        StageName.EXPLORE: StageConfig(
            name=StageName.EXPLORE,
            model="opus",
            thinking="high",
            repo_access=RepoAccess.RO,
            allow_network=True,
            allowed_tools=("Read", "Glob", "Grep", "Write", "WebFetch"),
        ),
        StageName.QA: StageConfig(
            name=StageName.QA,
            model="sonnet",
            thinking="medium",
            repo_access=RepoAccess.RO,
            allow_network=False,
            allowed_tools=("Read", "Glob", "Grep", "Write"),
        ),
        StageName.PLAN: StageConfig(
            name=StageName.PLAN,
            model="opus",
            thinking="high",
            repo_access=RepoAccess.RO,
            allow_network=True,
            allowed_tools=("Read", "Glob", "Grep", "Write", "WebFetch"),
        ),
        StageName.IMPLEMENT: StageConfig(
            name=StageName.IMPLEMENT,
            model="sonnet",
            thinking="high",
            repo_access=RepoAccess.RW,
            allow_network=False,
            allowed_tools=("Read", "Edit", "Write", "Glob", "Grep", "Bash"),
        ),
        StageName.VERIFY: StageConfig(
            name=StageName.VERIFY,
            model="sonnet",
            thinking="low",
            repo_access=RepoAccess.RW,
            allow_network=False,
            allowed_tools=(),
        ),
        StageName.REVIEW: StageConfig(
            name=StageName.REVIEW,
            model="opus",
            thinking="high",
            repo_access=RepoAccess.RO,
            allow_network=False,
            allowed_tools=("Read", "Glob", "Grep", "Write"),
        ),
        StageName.RETRO: StageConfig(
            name=StageName.RETRO,
            model="sonnet",
            thinking="medium",
            repo_access=RepoAccess.NONE,
            allow_network=False,
            allowed_tools=("Read", "Write"),
        ),
    }


def default_config() -> WorkflowConfig:
    """Build the default WorkflowConfig with XDG-friendly paths."""
    state_base = _default_state_base()
    return WorkflowConfig(
        repo_path=Path.cwd(),
        worktree_base=state_base / "worktrees",
        state_base=state_base,
        kb_path=Path.home() / "notes" / "work-kb",
        skills_base=_default_skills_base(),
        flake_path=None,
        verify_commands=(),
        max_plan_reviews=2,
        max_escalations=3,
        stages=default_stages(),
    )


def _expand_path(raw: str) -> Path:
    return Path(raw).expanduser()


def _apply_stage_overrides(
    base_stages: dict[StageName, StageConfig],
    raw_stages: dict[str, Any],
) -> dict[StageName, StageConfig]:
    stages = dict(base_stages)
    for key, patch in raw_stages.items():
        if not isinstance(patch, dict):
            raise ValueError(f"Stage override for {key!r} must be a JSON object")
        stage_name = StageName(key)
        current = stages[stage_name]
        mcp_raw = patch.get("mcp_config", current.mcp_config)
        mcp_path: Path | None
        if mcp_raw is None:
            mcp_path = None
        elif isinstance(mcp_raw, Path):
            mcp_path = mcp_raw
        else:
            mcp_path = _expand_path(str(mcp_raw))

        tools_raw = patch.get("allowed_tools", current.allowed_tools)
        if not isinstance(tools_raw, (list, tuple)) or any(
            not isinstance(tool, str) or not tool.strip() for tool in tools_raw
        ):
            raise ValueError(f"{key}.allowed_tools must contain nonempty strings")
        allow_network = patch.get("allow_network", current.allow_network)
        if not isinstance(allow_network, bool):
            raise ValueError(f"{key}.allow_network must be a boolean")
        thinking = patch.get("thinking", current.thinking)
        if thinking not in ("low", "medium", "high", "xhigh", "max"):
            raise ValueError(f"{key}.thinking has an unsupported level")

        stages[stage_name] = replace(
            current,
            model=str(patch.get("model", current.model)),
            thinking=thinking,
            repo_access=RepoAccess(patch.get("repo_access", current.repo_access)),
            allow_network=allow_network,
            mcp_config=mcp_path,
            allowed_tools=tuple(tools_raw),
        )
    return stages


def _load_shared_dependencies(raw: object) -> tuple[SharedDependency, ...]:
    """Parse [{"dir": "vendor", "lockfile": "composer.lock"}, ...]."""
    error = 'shared_dependencies must be a list of {"dir": ..., "lockfile": ...} objects'
    if not isinstance(raw, list):
        raise ValueError(error)
    deps: list[SharedDependency] = []
    for item in cast(list[object], raw):
        if not isinstance(item, dict):
            raise ValueError(error)
        fields = cast(dict[str, object], item)
        folder, lockfile = fields.get("dir"), fields.get("lockfile")
        if not isinstance(folder, str) or not folder.strip():
            raise ValueError(error)
        if not isinstance(lockfile, str) or not lockfile.strip():
            raise ValueError(error)
        deps.append(SharedDependency(dir=folder, lockfile=lockfile))
    return tuple(deps)


def load_config(config_path: Path | None) -> WorkflowConfig:
    """Load WorkflowConfig from JSON, falling back to XDG default or built-in defaults."""
    base = default_config()
    resolved_path = config_path
    if resolved_path is None:
        xdg_config = os.environ.get("XDG_CONFIG_HOME")
        candidate = (
            (Path(xdg_config) if xdg_config else Path.home() / ".config")
            / "claude-workflow"
            / "config.json"
        )
        if candidate.is_file():
            resolved_path = candidate

    if resolved_path is None:
        return base

    loaded = json.loads(resolved_path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError(f"Config file {resolved_path} must contain a JSON object")
    raw = cast(dict[str, Any], loaded)

    raw_stages = raw.get("stages")
    if "stages" in raw and not isinstance(raw_stages, dict):
        raise ValueError("stages must be a JSON object")
    stages = (
        _apply_stage_overrides(base.stages, raw_stages)
        if isinstance(raw_stages, dict)
        else base.stages
    )

    verify_raw = raw.get("verify_commands")
    if "verify_commands" in raw and (
        not isinstance(verify_raw, list)
        or any(not isinstance(cmd, str) or not cmd.strip() for cmd in verify_raw)
    ):
        raise ValueError("verify_commands must be a list of nonempty command strings")
    verify_commands = (
        tuple(str(cmd) for cmd in verify_raw)
        if isinstance(verify_raw, list)
        else base.verify_commands
    )

    max_plan_reviews = raw.get("max_plan_reviews", base.max_plan_reviews)
    max_escalations = raw.get("max_escalations", base.max_escalations)
    if type(max_plan_reviews) is not int or max_plan_reviews < 1:
        raise ValueError("max_plan_reviews must be a positive integer")
    if type(max_escalations) is not int or max_escalations < 0:
        raise ValueError("max_escalations must be a nonnegative integer")
    timeouts = {
        key: raw.get(key, getattr(base, key)) for key in ("headless_timeout", "verify_timeout")
    }
    for key, value in timeouts.items():
        if type(value) is not int or value <= 0:
            raise ValueError(f"{key} must be a positive number of seconds")
    commit_no_verify = raw.get("commit_no_verify", base.commit_no_verify)
    if not isinstance(commit_no_verify, bool):
        raise ValueError("commit_no_verify must be true or false")
    max_fix_rounds = raw.get("max_fix_rounds", base.max_fix_rounds)
    if type(max_fix_rounds) is not int or max_fix_rounds < 0:
        raise ValueError("max_fix_rounds must be a nonnegative integer")

    return WorkflowConfig(
        repo_path=_expand_path(str(raw["repo_path"])) if "repo_path" in raw else base.repo_path,
        worktree_base=(
            _expand_path(str(raw["worktree_base"]))
            if "worktree_base" in raw
            else base.worktree_base
        ),
        state_base=(
            _expand_path(str(raw["state_base"])) if "state_base" in raw else base.state_base
        ),
        kb_path=_expand_path(str(raw["kb_path"])) if "kb_path" in raw else base.kb_path,
        skills_base=(
            _expand_path(str(raw["skills_base"])) if "skills_base" in raw else base.skills_base
        ),
        flake_path=(
            _expand_path(str(raw["flake_path"]))
            if raw.get("flake_path") is not None
            else base.flake_path
        ),
        verify_commands=verify_commands,
        max_plan_reviews=max_plan_reviews,
        max_escalations=max_escalations,
        stages=stages,
        shared_dependencies=(
            _load_shared_dependencies(raw["shared_dependencies"])
            if "shared_dependencies" in raw
            else base.shared_dependencies
        ),
        max_fix_rounds=max_fix_rounds,
        headless_timeout=timeouts["headless_timeout"],
        verify_timeout=timeouts["verify_timeout"],
        commit_no_verify=commit_no_verify,
    )
