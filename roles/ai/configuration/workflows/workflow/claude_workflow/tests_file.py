"""Parse the tests.txt file that Plan writes (and Implement and Review may extend).

Each line is `<command-name> [name=value ...]`, split on whitespace, so a value can't
contain spaces. The command must exist in the config, and every value must belong to
a parameter with a `pattern` and fully match it. tests.txt is untrusted (Claude writes
it): `render` checks all of this again before anything runs.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from claude_workflow.commands import Command

TESTS_FILE = "tests.txt"

TESTS_LINE_FORMAT = "<command-name> [parameter=value ...]"


@dataclass(frozen=True)
class TestLine:
    """One valid line of tests.txt: a command name and its parameter values."""

    __test__ = False  # not a pytest test class

    command: str
    values: dict[str, str] = field(default_factory=dict[str, str])


def _parse_line(line: str, commands: dict[str, Command]) -> TestLine:
    """Parse one non-empty line (raises ValueError with the reason)."""
    name, *pairs = line.split()
    cmd = commands.get(name)
    if cmd is None:
        known = ", ".join(sorted(commands)) or "none"
        raise ValueError(f"unknown command {name!r} (known: {known})")
    values: dict[str, str] = {}
    for pair in pairs:
        key, sep, value = pair.partition("=")
        if not sep or not key:
            raise ValueError(f"expected parameter=value, got {pair!r}")
        param = cmd.parameters.get(key)
        if param is None:
            known = ", ".join(sorted(cmd.parameters)) or "none"
            raise ValueError(f"command {name!r} has no parameter {key!r} (known: {known})")
        if param.pattern is None:
            raise ValueError(f"parameter {key!r} has no pattern, so tests.txt cannot set it")
        if key in values:
            raise ValueError(f"parameter {key!r} is given twice")
        if re.fullmatch(param.pattern, value) is None:
            raise ValueError(f"value {value!r} for {key!r} does not match pattern {param.pattern!r}")
        values[key] = value
    return TestLine(name, values)


def parse_tests_file(
    text: str, commands: dict[str, Command]
) -> tuple[list[TestLine], list[str]]:
    """Return (valid lines, error messages). Blank lines and # comments are skipped."""
    lines: list[TestLine] = []
    errors: list[str] = []
    for number, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        try:
            lines.append(_parse_line(line, commands))
        except ValueError as exc:
            errors.append(f"line {number}: {exc}: {line!r}")
    return lines, errors
