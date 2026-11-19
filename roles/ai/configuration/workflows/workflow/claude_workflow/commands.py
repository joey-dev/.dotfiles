"""Named command models, parsed from the kebab-case config.

The config is validated against config.schema.json before these parsers run, so they
only convert; they do not re-check types. Rendering a command to an argv is Task 2.
"""

from __future__ import annotations

import fnmatch
import posixpath
import re
import shlex
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


class Skip(Exception):
    """A command has nothing to do (`if-none: skip` and no changed files match)."""


_PLACEHOLDER = re.compile(r"\{\{([A-Za-z0-9_-]+)\}\}")
_SLOT = re.compile(r"( ?)\{\{([A-Za-z0-9_-]+)\}\}")
_VALUE = re.compile(r"\{\{value\}\}")


def _select_changed(
    spec: ChangedFiles, changed: list[str], working_directory: str | None
) -> list[str]:
    prefix = working_directory.strip("/") + "/" if working_directory else ""
    picked: list[str] = []
    for path in changed:
        if not path.startswith(prefix):
            continue
        rel = path[len(prefix) :]
        if not any(fnmatch.fnmatchcase(rel, g) for g in spec.include):
            continue
        if any(fnmatch.fnmatchcase(rel, g) for g in spec.exclude):
            continue
        picked.append("./" + rel if rel.startswith("-") else rel)
    return picked


def render(
    cmd: Command,
    values: dict[str, str | ChangedFiles],
    changed: list[str],
    *,
    from_tests_file: bool,
) -> list[str]:
    """Render a command and parameter values to `["sh", "-c", line]`.

    Every inserted word is shell-quoted; the command and `format` text is trusted config.
    Values from tests.txt (`from_tests_file`) are untrusted and need a full-match pattern.
    """
    for name in values:
        if name not in cmd.parameters:
            raise ValueError(f"command {cmd.name!r}: unknown parameter {name!r}")

    for tok in tokens_inside_quotes(cmd.command, _PLACEHOLDER):
        raise ValueError(f"command {cmd.name!r}: placeholder {tok} sits inside quotes")
    for pname, p in cmd.parameters.items():
        if p.format is not None and tokens_inside_quotes(p.format, _VALUE):
            raise ValueError(
                f"command {cmd.name!r}, parameter {pname!r}: {{{{value}}}} in format sits inside quotes"
            )

    def fail(name: str, why: str) -> ValueError:
        return ValueError(f"command {cmd.name!r}, parameter {name!r}: {why}")

    def words_for(name: str, param: Parameter) -> list[str]:
        if name in values:
            value: str | ChangedFiles | None = values[name]
            from_user = from_tests_file
        else:
            value = param.default
            from_user = False
        if value is None:
            if param.required:
                raise fail(name, "required but no value given")
            return []
        if isinstance(value, ChangedFiles):
            if from_user:
                raise fail(name, "changed-files cannot be set from tests.txt")
            files = _select_changed(value, changed, cmd.working_directory)
            if not files:
                if value.if_none == "skip":
                    raise Skip(f"command {cmd.name!r}: no changed files match {name!r}")
                return []
            return files
        if from_user:
            if param.pattern is None:
                raise fail(name, "has no pattern, so it cannot be set from tests.txt")
            if "\n" in value or "\r" in value or "\x00" in value:
                raise fail(name, "value contains a newline or NUL")
            for word in value.split():
                if word.startswith("-"):
                    raise fail(name, f"word {word!r} starts with '-' (an option)")
                if ".." in word.split("/"):
                    raise fail(name, f"word {word!r} contains a '..' path segment")
            if re.fullmatch(param.pattern, value) is None:
                raise fail(name, f"value {value!r} does not match pattern {param.pattern!r}")
        words = value.split()
        if not words and param.required:
            raise fail(name, "required but empty")
        return words

    def replace(match: re.Match[str]) -> str:
        lead, name = match.group(1), match.group(2)
        param = cmd.parameters.get(name)
        if param is None:
            raise ValueError(f"command {cmd.name!r}: placeholder {{{{{name}}}}} has no parameter")
        words = words_for(name, param)
        if not words:
            return ""
        quoted = " ".join(shlex.quote(w) for w in words)
        if param.format is None:
            return lead + quoted
        return lead + param.format.replace("{{value}}", quoted)

    rendered = _SLOT.sub(replace, cmd.command)
    # Parameters not used in the command still get their required/pattern checks.
    for name, param in cmd.parameters.items():
        if f"{{{{{name}}}}}" not in cmd.command:
            words_for(name, param)
    return ["sh", "-c", rendered.strip()]


def tokens_inside_quotes(text: str, token: re.Pattern[str]) -> list[str]:
    """Return the `{{...}}` tokens of `text` that sit inside '...' or "..." quotes.

    Simple shell-quote scan: backslash escapes the next char outside quotes and inside
    double quotes; single quotes take everything literally. Inserted values are quoted by
    render(), so a token inside quotes would break that quoting.
    """
    found: list[str] = []
    quote = ""
    i = 0
    while i < len(text):
        ch = text[i]
        if ch == "\\" and quote != "'":
            i += 2
            continue
        if quote:
            if ch == quote:
                quote = ""
        elif ch in "'\"":
            quote = ch
        if quote and ch not in "'\"":
            match = token.match(text, i)
            if match:
                found.append(match.group(0))
                i = match.end()
                continue
        i += 1
    return found


# A host script path: plain characters only, so it can be found and replaced in the line.
_SCRIPT_WORD = re.compile(r"[A-Za-z0-9_./-]+")


def host_script(command: str) -> str:
    """The repo script a `host` command runs: its first word, a relative repo path.

    './test_runner.sh x' -> 'test_runner.sh'. Anything else is refused (ValueError):
    a PATH program such as `make` or `npm` would run worktree code (Makefile,
    package.json) on the host with nothing protected, and an absolute path is not in
    the repo. The word may only use [A-Za-z0-9_./-] and may not leave the repo.
    """
    first = command.split(maxsplit=1)[0] if command.strip() else ""
    if "/" not in first or first.startswith("/"):
        raise ValueError(
            f"host command must start with a repo script (a relative path such as "
            f"./test_runner.sh or bin/cs), not {first!r}"
        )
    if _SCRIPT_WORD.fullmatch(first) is None:
        raise ValueError(f"host repo script {first!r} may only use [A-Za-z0-9_./-]")
    script = posixpath.normpath(first)
    if script == "." or ".." in script.split("/"):
        raise ValueError(f"host repo script {first!r} leaves the repository")
    return script
