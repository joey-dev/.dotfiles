"""Parse the tests.txt file that the Plan stage writes.

Each line is `flake: <shell command>` (runs in the flake sandbox) or
`docker: <args>` (runs on the host through the test runner). Docker args are
split on whitespace and strictly validated, because they reach a host command.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

TESTS_FILE = "tests.txt"

DOCKER_TEST_TYPES: frozenset[str] = frozenset(
    {"unit", "integration", "api", "mobile-api", "acceptance", "codecept-build"}
)

_TOKEN = re.compile(r"^[A-Za-z0-9_./:=@,+-]+$")


@dataclass(frozen=True)
class TestLine:
    """One valid line of tests.txt."""

    __test__ = False  # not a pytest test class

    kind: Literal["flake", "docker"]
    text: str


def parse_tests_file(text: str) -> tuple[list[TestLine], list[str]]:
    """Return (valid lines, error messages). Blank lines and # comments are skipped."""
    lines: list[TestLine] = []
    errors: list[str] = []
    for number, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        kind, sep, rest = line.partition(":")
        rest = rest.strip()
        if not sep or kind not in ("flake", "docker") or not rest:
            errors.append(f"line {number}: expected 'flake: <command>' or 'docker: <args>', got {line!r}")
            continue
        lines.append(TestLine(kind, rest))  # type: ignore[arg-type]
    return lines, errors


def docker_args(text: str) -> list[str]:
    """Split docker test args on whitespace and validate them. Raises ValueError."""
    tokens = text.split()
    if not tokens:
        raise ValueError("docker args are empty")
    if tokens[0] not in DOCKER_TEST_TYPES:
        raise ValueError(f"unknown docker test type {tokens[0]!r}")
    for token in tokens:
        if not _TOKEN.match(token):
            raise ValueError(f"disallowed characters in docker arg {token!r}")
    return tokens
