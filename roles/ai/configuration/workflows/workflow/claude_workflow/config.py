"""Configuration models and the loader for global + per-repo kebab-case config."""

from __future__ import annotations

import json
import os
import re
from collections.abc import Sequence
from dataclasses import dataclass, field, replace
from enum import Enum
from pathlib import Path
from typing import Any, cast

from claude_workflow.commands import (
    Command,
    VerifyEntry,
    parse_commands,
    parse_duration,
    parse_verify,
)
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


DEFAULT_PROTECTED_PATHS: tuple[str, ...] = (
    "test_runner.sh",
    ".env",
    ".env.*",
    "docker-compose.yml",
    "docker-compose.*.yml",
    "docker-compose.yaml",
    "docker-compose.*.yaml",
    "compose.yml",
    "compose.yaml",
    "compose.*.yml",
    "compose.*.yaml",
    "legacy/docker/*",
    "nginx-proxy/*",
    "*Dockerfile",
    "*.Dockerfile",
    ".gitattributes",
    "*/.gitattributes",
)


@dataclass(frozen=True)
class DockerConfig:
    """Host-side Docker test stack settings (Claude never gets Docker access)."""

    project_name: str
    profile: str = "dyflexis"
    test_runner: str = "test_runner.sh"
    up_timeout: int = 900
    protected_paths: tuple[str, ...] = DEFAULT_PROTECTED_PATHS
    # Gitignored folders the stack mounts, copied from the main checkout before `up`.
    host_copies: tuple[str, ...] = ()
    # Gitignored folders the stack mounts that only need to exist (rebuilt by the app).
    create_dirs: tuple[str, ...] = ()


@dataclass(frozen=True)
class WorkflowConfig:
    """Top-level configuration for the workflow orchestrator."""

    repo_path: Path
    worktree_base: Path
    state_base: Path
    kb_path: Path
    skills_base: Path
    flake_path: Path | None
    max_plan_reviews: int
    max_escalations: int
    stages: dict[StageName, StageConfig]
    shared_dependencies: tuple[SharedDependency, ...] = ()
    max_fix_rounds: int = 3
    headless_timeout: int = 3600  # seconds per headless Claude call
    verify_timeout: int = 1800  # seconds per verify command (not in the config)
    commit_no_verify: bool = True  # skip git hooks for the final commit
    docker: DockerConfig | None = None
    commands: dict[str, Command] = field(default_factory=dict[str, Command])
    verify: tuple[VerifyEntry, ...] = ()
    # Old free-form verify commands; no longer loaded from config (removed in Task 4).
    verify_commands: tuple[str, ...] = ()


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
        max_plan_reviews=2,
        max_escalations=3,
        stages=default_stages(),
    )


def _expand_path(raw: str) -> Path:
    return Path(raw).expanduser()


# --- Loading: global.config.json + repository/<repo-name>.config.json -------------------

GLOBAL_FILE = "global.config.json"
REPO_DIR = "repository"
SCHEMA_FILE = "config.schema.json"
# The editable source of the config (the XDG copy is a read-only Nix store symlink).
DOTFILES_CONFIG_DIR = (
    Path.home() / ".dotfiles" / "roles" / "ai" / "configuration" / "workflows" / "config"
)

PathPart = str | int
_PLACEHOLDER = re.compile(r"\{\{([^{}]*)\}\}")


def default_config_dir() -> Path:
    """$XDG_CONFIG_HOME/claude-workflow (installed by home-manager)."""
    xdg_config = os.environ.get("XDG_CONFIG_HOME")
    return (Path(xdg_config) if xdg_config else Path.home() / ".config") / "claude-workflow"


def repo_config_path(config_dir: Path, repo_root: Path) -> Path:
    """repository/<repo-name>.config.json, where <repo-name> is the repo folder name."""
    return config_dir / REPO_DIR / f"{repo_root.name}.config.json"


def find_schema(config_dir: Path) -> Path:
    """The schema next to the config, else the copy shipped with the package."""
    candidates = [config_dir / SCHEMA_FILE]
    env = os.environ.get("CLAUDE_WORKFLOW_SCHEMA")
    if env:
        candidates.append(Path(env))
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise ValueError(f"config schema not found (looked in {', '.join(map(str, candidates))})")


def _read_json(path: Path) -> dict[str, Any]:
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path}: invalid JSON: {exc}") from exc
    if not isinstance(loaded, dict):
        raise ValueError(f"{path}: must contain a JSON object")
    return cast(dict[str, Any], loaded)


def merge_config(global_raw: dict[str, Any], repo_raw: dict[str, Any]) -> dict[str, Any]:
    """Deep merge: objects merge key by key; arrays and scalars from the repo replace."""
    merged = dict(global_raw)
    for key, value in repo_raw.items():
        current = merged.get(key)
        if isinstance(current, dict) and isinstance(value, dict):
            merged[key] = merge_config(cast(dict[str, Any], current), cast(dict[str, Any], value))
        else:
            merged[key] = value
    return merged


def _format_path(parts: Sequence[PathPart]) -> str:
    text = "$"
    for part in parts:
        text += f"[{part}]" if isinstance(part, int) else f".{part}"
    return text


def _cross_check(raw: dict[str, Any]) -> list[tuple[list[PathPart], str]]:
    """Checks the schema can't express: references between commands and verify."""
    errors: list[tuple[list[PathPart], str]] = []
    commands_raw = raw.get("commands")
    commands = cast(dict[str, Any], commands_raw) if isinstance(commands_raw, dict) else {}
    for name, cmd in commands.items():
        if not isinstance(cmd, dict):
            continue
        cmd = cast(dict[str, Any], cmd)
        params_raw = cmd.get("parameters")
        params = cast(dict[str, Any], params_raw) if isinstance(params_raw, dict) else {}
        line = cmd.get("command")
        if isinstance(line, str):
            for placeholder in dict.fromkeys(_PLACEHOLDER.findall(line)):
                if placeholder not in params:
                    errors.append(
                        (
                            ["commands", name, "command"],
                            f"placeholder '{{{{{placeholder}}}}}' has no parameter '{placeholder}'",
                        )
                    )
        is_container = cmd.get("run-in") == "container"
        if is_container and "container" not in cmd:
            errors.append((["commands", name], "run-in 'container' needs 'container'"))
        if not is_container:
            for key in ("container", "user"):
                if key in cmd:
                    errors.append((["commands", name, key], "only allowed with run-in 'container'"))
    verify_raw = raw.get("verify")
    verify = cast(list[object], verify_raw) if isinstance(verify_raw, list) else []
    for index, entry in enumerate(verify):
        if not isinstance(entry, dict):
            continue
        entry = cast(dict[str, Any], entry)
        run = entry.get("run")
        if not isinstance(run, str):
            continue
        if run not in commands:
            errors.append((["verify", index, "run"], f"unknown command '{run}'"))
            continue
        cmd_params = cast(dict[str, Any], commands[run]).get("parameters")
        known = cast(dict[str, Any], cmd_params) if isinstance(cmd_params, dict) else {}
        values = entry.get("parameters")
        for param in cast(dict[str, Any], values) if isinstance(values, dict) else {}:
            if param not in known:
                errors.append(
                    (
                        ["verify", index, "parameters", param],
                        f"command '{run}' has no parameter '{param}'",
                    )
                )
    return errors


def _validate(raw: dict[str, Any], schema_path: Path) -> list[tuple[list[PathPart], str]]:
    import jsonschema  # imported here: only needed when loading a config

    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validator: Any = jsonschema.Draft202012Validator(schema)
    found = cast(list[jsonschema.ValidationError], list(validator.iter_errors(raw)))
    errors: list[tuple[list[PathPart], str]] = []
    for error in sorted(found, key=lambda e: list(map(str, e.path))):
        # The command's container/user rule (an if/then/else under allOf) is reported
        # by _cross_check with a readable message.
        if "allOf" in error.absolute_schema_path:
            continue
        errors.append((list(error.absolute_path), error.message))
    return errors + _cross_check(raw)


def validate_raw(raw: dict[str, Any], schema_path: Path) -> list[str]:
    """Schema errors plus cross checks, as '$.path: message'."""
    return [f"{_format_path(path)}: {message}" for path, message in _validate(raw, schema_path)]


def _prefix_depth(raw: object, parts: Sequence[PathPart]) -> int:
    depth = 0
    for part in parts:
        if isinstance(raw, dict) and isinstance(part, str) and part in raw:
            raw = cast(dict[str, Any], raw)[part]
        elif (
            isinstance(raw, list)
            and isinstance(part, int)
            and part < len(items := cast(list[Any], raw))
        ):
            raw = items[part]
        else:
            break
        depth += 1
    return depth


@dataclass(frozen=True)
class _Sources:
    global_path: Path
    global_raw: dict[str, Any]
    repo_path: Path
    repo_raw: dict[str, Any]

    def merged(self) -> dict[str, Any]:
        return merge_config(self.global_raw, self.repo_raw)

    def source_of(self, parts: Sequence[PathPart]) -> Path:
        """The file a key came from: the one that holds the longest part of its path."""
        repo_depth = _prefix_depth(self.repo_raw, parts)
        if repo_depth and repo_depth >= _prefix_depth(self.global_raw, parts):
            return self.repo_path
        return self.global_path


def _read_sources(repo_root: Path, config_dir: Path) -> _Sources:
    global_path = config_dir / GLOBAL_FILE
    if not global_path.is_file():
        raise ValueError(f"missing global config: {global_path}")
    repo_path = repo_config_path(config_dir, repo_root)
    return _Sources(
        global_path=global_path,
        global_raw=_read_json(global_path),
        repo_path=repo_path,
        repo_raw=_read_json(repo_path) if repo_path.is_file() else {},
    )


def _source_errors(sources: _Sources, schema_path: Path) -> list[str]:
    return [
        f"{sources.source_of(path)}: {_format_path(path)}: {message}"
        for path, message in _validate(sources.merged(), schema_path)
    ]


def check_config(repo_root: Path, config_dir: Path | None = None) -> list[str]:
    """All config errors, each prefixed with the file the key came from."""
    config_dir = config_dir or default_config_dir()
    try:
        sources = _read_sources(repo_root, config_dir)
        return _source_errors(sources, find_schema(config_dir))
    except ValueError as exc:
        return [str(exc)]


def render_full_config(repo_root: Path, config_dir: Path, out_dir: Path) -> tuple[Path, list[str]]:
    """Write full-configs/<repo-name>.config.json (merged; for reading only) and validate.

    The workflow never reads this file: it always merges the sources itself.
    """
    out_path = out_dir / f"{repo_root.name}.config.json"
    try:
        sources = _read_sources(repo_root, config_dir)
        schema_path = find_schema(config_dir)
    except ValueError as exc:
        return out_path, [str(exc)]
    out_dir.mkdir(parents=True, exist_ok=True)
    # Point $schema at the schema used, so editors validate it wherever it is written.
    rendered = {**sources.merged(), "$schema": str(schema_path.resolve())}
    out_path.write_text(json.dumps(rendered, indent=2) + "\n", encoding="utf-8")
    return out_path, _source_errors(sources, schema_path)


def _stages(raw: dict[str, Any]) -> dict[StageName, StageConfig]:
    stages = default_stages()
    for key, patch in raw.items():
        name = StageName(key)
        current = stages[name]
        fields = cast(dict[str, Any], patch)
        mcp_raw = fields.get("mcp-config", current.mcp_config)
        stages[name] = replace(
            current,
            model=fields.get("model", current.model),
            thinking=fields.get("thinking", current.thinking),
            repo_access=RepoAccess(fields.get("repo-access", current.repo_access)),
            allow_network=fields.get("allow-network", current.allow_network),
            mcp_config=None if mcp_raw is None else _expand_path(str(mcp_raw)),
            allowed_tools=tuple(fields.get("allowed-tools", current.allowed_tools)),
        )
    return stages


def _docker(raw: dict[str, Any] | None) -> DockerConfig | None:
    if raw is None:
        return None
    defaults = DockerConfig(project_name=raw["project-name"])
    return replace(
        defaults,
        profile=raw.get("profile", defaults.profile),
        up_timeout=(
            parse_duration(raw["up-timeout"]) if "up-timeout" in raw else defaults.up_timeout
        ),
        # Extra patterns: the defaults are always protected.
        protected_paths=(*DEFAULT_PROTECTED_PATHS, *raw.get("protected-paths", ())),
        host_copies=tuple(raw.get("host-copies", ())),
        create_dirs=tuple(raw.get("create-dirs", ())),
    )


def load_config(repo_root: Path, config_dir: Path | None = None) -> WorkflowConfig:
    """Load global.config.json + repository/<repo-name>.config.json, validated.

    Raises ValueError listing every error (each naming its source file).
    """
    config_dir = config_dir or default_config_dir()
    sources = _read_sources(repo_root, config_dir)
    errors = _source_errors(sources, find_schema(config_dir))
    if errors:
        raise ValueError("invalid config:\n" + "\n".join(errors))
    raw = sources.merged()
    base = default_config()
    flake = raw.get("flake-path")
    return replace(
        base,
        repo_path=repo_root,
        kb_path=_expand_path(raw["kb-path"]) if "kb-path" in raw else base.kb_path,
        flake_path=None if flake is None else _expand_path(flake),
        max_plan_reviews=raw.get("max-plan-reviews", base.max_plan_reviews),
        max_escalations=raw.get("max-escalations", base.max_escalations),
        max_fix_rounds=raw.get("max-fix-rounds", base.max_fix_rounds),
        headless_timeout=(
            parse_duration(raw["headless-timeout"])
            if "headless-timeout" in raw
            else base.headless_timeout
        ),
        commit_no_verify=raw.get("commit-no-verify", base.commit_no_verify),
        stages=_stages(raw.get("stages", {})),
        shared_dependencies=tuple(
            SharedDependency(dir=d["dir"], lockfile=d["lockfile"])
            for d in raw.get("shared-dependencies", ())
        ),
        docker=_docker(raw.get("docker-compose")),
        commands=parse_commands(raw.get("commands", {})),
        verify=parse_verify(raw.get("verify", [])),
    )
