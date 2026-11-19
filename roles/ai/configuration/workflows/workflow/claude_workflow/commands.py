"""Named command models, parsed from the kebab-case config.

The config is validated against config.schema.json before these parsers run, so they
only convert; they do not re-check types. Rendering a command to an argv is Task 2.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Literal, cast

RunIn = Literal["sandbox", "host", "container"]
IfNone = Literal["skip", "run-without"]

DEFAULT_COMMAND_TIMEOUT = "30m"

_DURATION = re.compile(r"[1-9][0-9]*(s|m|h)")
_UNIT_SECONDS = {"s": 1, "m": 60, "h": 3600}


def parse_duration(text: str) -> int:
    """'90s' / '15m' / '2h' -> seconds. Anything else raises ValueError."""
    match = _DURATION.fullmatch(text)
    if match is None:
        raise ValueError(f"invalid duration {text!r}: use e.g. '90s', '15m' or '2h'")
    return int(text[:-1]) * _UNIT_SECONDS[match.group(1)]


@dataclass(frozen=True)
class ChangedFiles:
    """The files changed on the ticket, filtered by fnmatch globs."""

    include: tuple[str, ...] = ("*",)
    exclude: tuple[str, ...] = ()
    if_none: IfNone = "skip"


@dataclass(frozen=True)
class Parameter:
    """One `{{name}}` placeholder of a command."""

    description: str = ""
    required: bool = False
    default: str | ChangedFiles | None = None
    format: str | None = None
    pattern: str | None = None
    example: str | None = None


@dataclass(frozen=True)
class Command:
    """A named command from the config's `commands` object."""

    name: str
    description: str
    run_in: RunIn
    command: str
    working_directory: str | None
    timeout: int  # seconds
    needs_compose_stack: bool
    needs_git: bool
    container: str | None
    user: str | None
    parameters: dict[str, Parameter] = field(default_factory=dict[str, Parameter])


@dataclass(frozen=True)
class VerifyEntry:
    """One entry of `verify`: a command name plus parameter values."""

    run: str
    values: dict[str, str | ChangedFiles] = field(default_factory=dict[str, str | ChangedFiles])


def _changed_files(raw: dict[str, Any]) -> ChangedFiles:
    spec = cast(dict[str, Any], raw["changed-files"])
    return ChangedFiles(
        include=tuple(spec.get("include", ("*",))),
        exclude=tuple(spec.get("exclude", ())),
        if_none=spec.get("if-none", "skip"),
    )


def _value(raw: object) -> str | ChangedFiles:
    if isinstance(raw, dict):
        return _changed_files(cast(dict[str, Any], raw))
    return str(raw)


def _parameter(raw: dict[str, Any]) -> Parameter:
    default = raw.get("default")
    return Parameter(
        description=raw.get("description", ""),
        required=raw.get("required", False),
        default=None if default is None else _value(default),
        format=raw.get("format"),
        pattern=raw.get("pattern"),
        example=raw.get("example"),
    )


def parse_command(name: str, raw: dict[str, Any]) -> Command:
    """Build a Command from one (schema-valid) entry of `commands`."""
    params = cast(dict[str, dict[str, Any]], raw.get("parameters", {}))
    return Command(
        name=name,
        description=raw.get("description", ""),
        run_in=raw["run-in"],
        command=raw["command"],
        working_directory=raw.get("working-directory"),
        timeout=parse_duration(raw.get("timeout", DEFAULT_COMMAND_TIMEOUT)),
        needs_compose_stack=raw.get("needs-compose-stack", False),
        needs_git=raw.get("needs-git", False),
        container=raw.get("container"),
        user=raw.get("user"),
        parameters={key: _parameter(value) for key, value in params.items()},
    )


def parse_commands(raw: dict[str, Any]) -> dict[str, Command]:
    """Build all commands from the config's `commands` object."""
    return {name: parse_command(name, value) for name, value in raw.items()}


def parse_verify(raw: list[dict[str, Any]]) -> tuple[VerifyEntry, ...]:
    """Build the `verify` entries."""
    entries: list[VerifyEntry] = []
    for item in raw:
        values = cast(dict[str, object], item.get("parameters", {}))
        entries.append(
            VerifyEntry(run=item["run"], values={k: _value(v) for k, v in values.items()})
        )
    return tuple(entries)
