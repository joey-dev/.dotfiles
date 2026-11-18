"""Tests for the tests.txt parser."""

from __future__ import annotations

import pytest

from claude_workflow.tests_file import TestLine, docker_args, parse_tests_file


def test_parses_flake_and_docker_lines() -> None:
    lines, errors = parse_tests_file(
        "# comment\n\nflake: cd frontend && pnpm run test:unit a.spec.ts\ndocker: api FooCest\n"
    )
    assert errors == []
    assert lines == [
        TestLine("flake", "cd frontend && pnpm run test:unit a.spec.ts"),
        TestLine("docker", "api FooCest"),
    ]


def test_unknown_prefix_is_an_error_with_line_number() -> None:
    _, errors = parse_tests_file("flake: ok\nshell: rm -rf /\n")
    assert len(errors) == 1 and "line 2" in errors[0]


def test_docker_args_split_without_shell() -> None:
    assert docker_args("unit --group foo tests/Unit/FooTest.php") == [
        "unit",
        "--group",
        "foo",
        "tests/Unit/FooTest.php",
    ]


@pytest.mark.parametrize("bad", ["api ; rm -rf ~", "api `x`", "api $(x)", "api a|b", "api 'x'"])
def test_docker_args_reject_shell_characters(bad: str) -> None:
    with pytest.raises(ValueError):
        docker_args(bad)


@pytest.mark.parametrize("bad", ["", "debug api", "shell api", "phpunit"])
def test_docker_args_reject_unknown_type(bad: str) -> None:
    with pytest.raises(ValueError):
        docker_args(bad)
