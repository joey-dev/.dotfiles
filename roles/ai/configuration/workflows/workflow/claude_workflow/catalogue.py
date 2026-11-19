"""The command catalogue for prompts, generated from the config's `commands`.

Plan, Implement and Review see each command's name, description, run-in and
parameters, so they can write tests.txt lines. Implement also sees the rendered line
of each `sandbox` command, so it can run that check itself. The raw `command` text of
host and container commands is never shown: Claude can't run those anyway.
"""

from __future__ import annotations

import re

from claude_workflow.commands import (
    ChangedFiles,
    Command,
    Parameter,
    Skip,
    VerifyEntry,
    render,
)
from claude_workflow.tests_file import TESTS_FILE, TESTS_LINE_FORMAT


def describe_values(name: str, values: dict[str, str | ChangedFiles]) -> str:
    """A readable label: `phpstan paths="Core Common" files=<changed files>`."""
    parts = [name]
    for key, value in values.items():
        if isinstance(value, ChangedFiles):
            parts.append(f"{key}=<changed files>")
        elif not value or any(ch.isspace() for ch in value):
            parts.append(f'{key}="{value}"')
        else:
            parts.append(f"{key}={value}")
    return " ".join(parts)


def _settable_example(param: Parameter) -> str | None:
    """The example value if a tests.txt line could use it as is."""
    if param.pattern is None or not param.example or param.example.split() != [param.example]:
        return None
    return param.example if re.fullmatch(param.pattern, param.example) else None


def _parameter_line(name: str, param: Parameter) -> str:
    flags = ["required"] if param.required else []
    flags.append("settable in tests.txt" if param.pattern is not None else "not in tests.txt")
    text = f"  - `{name}` ({', '.join(flags)})"
    details: list[str] = []
    if param.description:
        details.append(param.description.rstrip("."))
    if param.example:
        details.append(f"Example: `{param.example}`")
    if isinstance(param.default, ChangedFiles):
        details.append(f"Default: the changed files matching {' '.join(param.default.include)}")
    elif param.default:
        details.append(f"Default: `{param.default}`")
    return text + (": " + ". ".join(details) + "." if details else "")


def _example_line(cmd: Command) -> str | None:
    """An example tests.txt line; None when a required parameter has no usable example."""
    words = [cmd.name]
    for name, param in cmd.parameters.items():
        example = _settable_example(param)
        if example is not None:
            words.append(f"{name}={example}")
        elif param.required and param.default is None:
            return None
    return " ".join(words)


def _run_line(cmd: Command) -> str | None:
    """The rendered line for the example values, for a sandbox command Implement may run."""
    values: dict[str, str | ChangedFiles] = {
        name: param.example for name, param in cmd.parameters.items() if param.example
    }
    try:
        return render(cmd, values, [], from_tests_file=False)[2]
    except (ValueError, Skip):
        return None


def command_catalogue(commands: dict[str, Command], *, run_lines: bool = False) -> str:
    """The catalogue text; empty when there are no commands.

    run_lines: show how to run each `sandbox` command (Implement only).
    """
    if not commands:
        return ""
    out = [
        f"Commands for {TESTS_FILE} (one per line: `{TESTS_LINE_FORMAT}`; a value cannot "
        "contain spaces; only parameters marked 'settable in tests.txt' can be set):"
    ]
    for cmd in commands.values():
        head = f"- `{cmd.name}` (run-in: {cmd.run_in})"
        out.append(f"{head}: {cmd.description}" if cmd.description else head)
        out += [_parameter_line(name, param) for name, param in cmd.parameters.items()]
        example = _example_line(cmd)
        if example is not None and example != cmd.name:
            out.append(f"  - {TESTS_FILE} example: `{example}`")
        if not run_lines:
            continue
        if cmd.run_in != "sandbox" or cmd.needs_git:
            out.append("  - Runs only in Verify.")
            continue
        line = _run_line(cmd)
        if line is not None:
            where = f" (in `{cmd.working_directory}/`)" if cmd.working_directory else ""
            out.append(f"  - Run it yourself{where}: `{line}`")
    return "\n".join(out) + "\n"


def verify_summary(verify: tuple[VerifyEntry, ...]) -> str:
    """`Verify always runs: `a`; `b x=1`. ` or empty."""
    if not verify:
        return ""
    items = "; ".join(f"`{describe_values(e.run, e.values)}`" for e in verify)
    return f"Verify always runs: {items}. "
