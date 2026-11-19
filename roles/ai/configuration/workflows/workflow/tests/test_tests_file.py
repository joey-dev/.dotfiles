"""Tests for the tests.txt parser: `<command-name> [name=value ...]` lines."""

from __future__ import annotations

from typing import Any

from claude_workflow.commands import Command, Parameter
from claude_workflow.tests_file import TestLine, parse_tests_file


def _cmd(name: str, **params: Parameter) -> Command:
    fields: dict[str, Any] = {
        "name": name,
        "description": "",
        "run_in": "sandbox",
        "command": f"run {' '.join('{{' + p + '}}' for p in params)}",
        "working_directory": None,
        "timeout": 60,
        "needs_compose_stack": False,
        "needs_git": False,
        "container": None,
        "user": None,
        "parameters": dict(params),
    }
    return Command(**fields)


COMMANDS = {
    "phpunit": _cmd("phpunit", filter=Parameter(pattern=r"[A-Za-z0-9_\\:.-]+")),
    "tests:api": _cmd("tests:api", filter=Parameter(required=True, pattern=r"[A-Za-z0-9_./:-]+")),
    "phpstan": _cmd("phpstan", paths=Parameter()),  # no pattern: not settable
}


def test_tests_line_with_values() -> None:
    lines, errors = parse_tests_file(
        "# comment\n\nphpunit\nphpunit filter=InvoiceTest\n  tests:api   filter=a/B.php  \n",
        COMMANDS,
    )
    assert errors == []
    assert lines == [
        TestLine("phpunit", {}),
        TestLine("phpunit", {"filter": "InvoiceTest"}),
        TestLine("tests:api", {"filter": "a/B.php"}),
    ]


def test_tests_line_unknown_command() -> None:
    lines, errors = parse_tests_file("phpunit\nflake: rm -rf /\n", COMMANDS)
    assert lines == [TestLine("phpunit", {})]
    assert len(errors) == 1
    assert "line 2" in errors[0] and "flake:" in errors[0]


def test_tests_line_value_fails_pattern() -> None:
    lines, errors = parse_tests_file("phpunit filter=a;rm\nphpunit filter=$(id)\n", COMMANDS)
    assert lines == []
    assert [e.split(":")[0] for e in errors] == ["line 1", "line 2"]
    assert "pattern" in errors[0]


def test_tests_line_unknown_parameter() -> None:
    _, errors = parse_tests_file("phpunit Filter=Foo\n", COMMANDS)
    assert len(errors) == 1 and "line 1" in errors[0] and "Filter" in errors[0]


def test_tests_line_parameter_without_pattern_is_refused() -> None:
    _, errors = parse_tests_file("phpstan paths=src\n", COMMANDS)
    assert len(errors) == 1 and "line 1" in errors[0] and "pattern" in errors[0]


def test_tests_line_needs_key_value_and_no_duplicates() -> None:
    _, errors = parse_tests_file(
        "phpunit InvoiceTest\nphpunit =x\nphpunit filter=A filter=B\n", COMMANDS
    )
    assert [e.split(":")[0] for e in errors] == ["line 1", "line 2", "line 3"]
