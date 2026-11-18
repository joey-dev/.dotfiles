"""Intake uses the repo's own Atlassian MCP server (.mcp.json + ~/.mcp-auth)."""

from __future__ import annotations

import os
from dataclasses import replace
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from claude_workflow.claude_runner import ClaudeResult
from claude_workflow.config import StageName, WorkflowConfig, default_config
from claude_workflow.sandbox import copy_mcp_auth_in
from claude_workflow.stages.base import StageContext, StageOutcome, build_stage_sandbox
from claude_workflow.stages.intake import IntakeStage
from claude_workflow.state import TicketState


def _config(tmp_path: Path, with_mcp_json: bool = True) -> WorkflowConfig:
    repo = tmp_path / "repo"
    repo.mkdir()
    if with_mcp_json:
        (repo / ".mcp.json").write_text('{"mcpServers": {}}')
    return replace(
        default_config(), repo_path=repo, state_base=tmp_path, skills_base=tmp_path / "skills"
    )


def _ctx(config: WorkflowConfig) -> StageContext:
    state_dir = config.state_base / "PROJ-1"
    state_dir.mkdir(exist_ok=True)
    return StageContext("PROJ-1", config, TicketState("PROJ-1"), state_dir)


def test_default_intake_tools_are_company_server() -> None:
    tools = default_config().stages[StageName.INTAKE].allowed_tools

    assert "mcp__Atlassian-Rovo-MCP__*" in tools
    assert not any("claude_ai" in tool for tool in tools)


def test_intake_gets_repo_mcp_json(tmp_path: Path) -> None:
    config = _config(tmp_path)
    ctx = _ctx(config)

    intake = build_stage_sandbox(ctx, StageName.INTAKE, repo_dir=None, kb_dir=None,
                                 workdir=ctx.state_dir)
    explore = build_stage_sandbox(ctx, StageName.EXPLORE, repo_dir=None, kb_dir=None,
                                  workdir=ctx.state_dir)

    assert intake.mcp_config == config.repo_path / ".mcp.json"
    assert explore.mcp_config is None  # no mcp__ tools, so no MCP servers


def test_intake_without_mcp_json_has_no_mcp_config(tmp_path: Path) -> None:
    ctx = _ctx(_config(tmp_path, with_mcp_json=False))

    spec = build_stage_sandbox(ctx, StageName.INTAKE, repo_dir=None, kb_dir=None,
                               workdir=ctx.state_dir)

    assert spec.mcp_config is None


def test_intake_failure_mentions_mcp_server(tmp_path: Path, monkeypatch: Any) -> None:
    monkeypatch.setattr(Path, "home", lambda: tmp_path / "empty-home")
    ctx = _ctx(_config(tmp_path))

    with patch(
        "claude_workflow.stages.base.run_claude_headless",
        return_value=ClaudeResult(0, "", "", None),
    ):
        result = IntakeStage().run(ctx)

    assert result.outcome is StageOutcome.FAILED
    assert ".mcp.json" in result.message
    assert "~/.mcp-auth" in result.message


# --- copying the mcp-remote login (~/.mcp-auth) into the sandbox ---


def _auth_setup(tmp_path: Path, monkeypatch: Any) -> tuple[Path, Path]:
    home = tmp_path / "host_home"
    host_file = home / ".mcp-auth" / "mcp-remote-v1" / "abc_tokens.json"
    host_file.parent.mkdir(parents=True)
    host_file.write_text("host v1")
    monkeypatch.setattr(Path, "home", lambda: home)
    state_dir = tmp_path / "state"
    (state_dir / "home").mkdir(parents=True)
    sandbox_file = state_dir / "home" / ".mcp-auth" / "mcp-remote-v1" / "abc_tokens.json"
    return host_file, sandbox_file


def _age(path: Path, seconds: int) -> None:
    stamp = path.stat().st_mtime + seconds
    os.utime(path, (stamp, stamp))


def test_mcp_auth_is_copied_in(tmp_path: Path, monkeypatch: Any) -> None:
    _host, sandbox = _auth_setup(tmp_path, monkeypatch)

    copy_mcp_auth_in(tmp_path / "state")

    assert sandbox.read_text() == "host v1"
    assert sandbox.stat().st_mode & 0o777 == 0o600


def test_newer_host_mcp_auth_replaces_sandbox_copy(tmp_path: Path, monkeypatch: Any) -> None:
    host, sandbox = _auth_setup(tmp_path, monkeypatch)
    copy_mcp_auth_in(tmp_path / "state")
    host.write_text("host v2")
    _age(host, +10)

    copy_mcp_auth_in(tmp_path / "state")

    assert sandbox.read_text() == "host v2"


def test_sandbox_refreshed_mcp_auth_is_kept_and_host_untouched(
    tmp_path: Path, monkeypatch: Any
) -> None:
    host, sandbox = _auth_setup(tmp_path, monkeypatch)
    copy_mcp_auth_in(tmp_path / "state")
    sandbox.write_text("refreshed in sandbox")
    _age(sandbox, +10)

    copy_mcp_auth_in(tmp_path / "state")

    assert sandbox.read_text() == "refreshed in sandbox"
    assert host.read_text() == "host v1"


def test_planted_symlink_folder_in_sandbox_is_refused(tmp_path: Path, monkeypatch: Any) -> None:
    _host, sandbox = _auth_setup(tmp_path, monkeypatch)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    sandbox.parent.parent.mkdir(parents=True)
    sandbox.parent.symlink_to(elsewhere)

    with pytest.raises(RuntimeError, match="symlink"):
        copy_mcp_auth_in(tmp_path / "state")
    assert not any(elsewhere.iterdir())


def test_host_symlinks_in_mcp_auth_are_skipped(tmp_path: Path, monkeypatch: Any) -> None:
    host, sandbox = _auth_setup(tmp_path, monkeypatch)
    secret = tmp_path / "secret.txt"
    secret.write_text("not for the sandbox")
    (host.parent / "link.json").symlink_to(secret)

    copy_mcp_auth_in(tmp_path / "state")

    assert not (sandbox.parent / "link.json").exists()
