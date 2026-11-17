"""Tests for claude_workflow.claude_runner."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from claude_workflow.claude_runner import (
    run_claude_headless,
    run_claude_interactive,
)
from claude_workflow.config import RepoAccess, StageConfig, StageName
from claude_workflow.sandbox import SandboxSpec


def _make_sandbox(tmp_path: Path) -> SandboxSpec:
    state_dir = tmp_path / "state"
    state_dir.mkdir(exist_ok=True)
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir(exist_ok=True)
    return SandboxSpec(
        repo_dir=repo_dir,
        repo_access=RepoAccess.RO,
        state_dir=state_dir,
        skills_dirs=(),
        kb_dir=None,
        allow_network=False,
        workdir=repo_dir,
    )


def test_headless_builds_expected_claude_flags(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    captured: list[list[str]] = []

    def fake_run(cmd: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        captured.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, stdout="ok", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    mcp = tmp_path / "mcp.json"
    stage = StageConfig(
        name=StageName.INTAKE,
        model="sonnet",
        thinking="medium",
        repo_access=RepoAccess.NONE,
        allow_network=True,
        mcp_config=mcp,
        allowed_tools=("Read", "Write"),
    )
    res = run_claude_headless(stage, _make_sandbox(tmp_path), "fetch ticket")

    assert res.returncode == 0
    assert res.stdout == "ok"
    cmd = captured[0]
    inner = cmd[cmd.index("--") + 1 :]
    assert inner[0] == "claude"
    assert "-p" in inner
    assert "fetch ticket" in inner
    assert "--model" in inner
    assert "sonnet" in inner
    assert "--allowedTools" in inner
    assert "Read,Write" in inner
    assert "--mcp-config" in inner
    assert str(mcp) in inner


def test_interactive_uses_session_id_or_resume(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    captured: list[list[str]] = []

    def fake_run(cmd: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        captured.append(cmd)
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(subprocess, "run", fake_run)

    stage = StageConfig(
        name=StageName.QA,
        model="sonnet",
        thinking="medium",
        repo_access=RepoAccess.RO,
        allow_network=False,
        allowed_tools=("Read", "Write"),
    )
    sandbox = _make_sandbox(tmp_path)

    rc1 = run_claude_interactive(stage, sandbox, "start qa", session_id="uuid-1", resume=False)
    rc2 = run_claude_interactive(stage, sandbox, "continue", session_id="uuid-1", resume=True)

    assert rc1 == 0
    assert rc2 == 0
    inner1 = captured[0][captured[0].index("--") + 1 :]
    inner2 = captured[1][captured[1].index("--") + 1 :]
    assert inner1[1:3] == ["--session-id", "uuid-1"]
    assert inner2[1:3] == ["--resume", "uuid-1"]
