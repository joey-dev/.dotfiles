"""Tests for parsing the command models in claude_workflow.commands."""

from __future__ import annotations

from claude_workflow.commands import (
    ChangedFiles,
    Command,
    Parameter,
    VerifyEntry,
    parse_commands,
    parse_verify,
)


def test_command_defaults() -> None:
    commands = parse_commands({"lint": {"run-in": "sandbox", "command": "lint"}})

    assert commands == {
        "lint": Command(
            name="lint",
            description="",
            run_in="sandbox",
            command="lint",
            working_directory=None,
            timeout=1800,
            needs_compose_stack=False,
            needs_git=False,
            container=None,
            user=None,
            parameters={},
        )
    }


def test_command_with_all_fields() -> None:
    raw = {
        "composer": {
            "description": "Install.",
            "run-in": "container",
            "command": "composer install {{flags}}",
            "working-directory": "legacy",
            "timeout": "5m",
            "needs-compose-stack": True,
            "needs-git": True,
            "container": "web",
            "user": "1000:1000",
            "parameters": {
                "flags": {
                    "description": "Flags.",
                    "required": True,
                    "default": "--no-dev",
                    "format": "{{value}}",
                    "pattern": "^--[a-z-]+$",
                    "example": "--no-dev",
                }
            },
        }
    }

    cmd = parse_commands(raw)["composer"]

    assert (cmd.timeout, cmd.needs_compose_stack, cmd.needs_git) == (300, True, True)
    assert (cmd.container, cmd.user, cmd.working_directory) == ("web", "1000:1000", "legacy")
    assert cmd.parameters["flags"] == Parameter(
        description="Flags.",
        required=True,
        default="--no-dev",
        format="{{value}}",
        pattern="^--[a-z-]+$",
        example="--no-dev",
    )


def test_default_can_be_changed_files() -> None:
    raw = {
        "stan": {
            "run-in": "sandbox",
            "command": "stan {{paths}}",
            "parameters": {"paths": {"default": {"changed-files": {"exclude": ["*Test.php"]}}}},
        }
    }

    param = parse_commands(raw)["stan"].parameters["paths"]

    assert param.default == ChangedFiles(include=("*",), exclude=("*Test.php",), if_none="skip")


def test_parse_verify() -> None:
    raw = [
        {"run": "a"},
        {"run": "b", "parameters": {"x": "1", "y": {"changed-files": {"if-none": "run-without"}}}},
    ]

    assert parse_verify(raw) == (
        VerifyEntry(run="a", values={}),
        VerifyEntry(
            run="b",
            values={"x": "1", "y": ChangedFiles(include=("*",), exclude=(), if_none="run-without")},
        ),
    )
