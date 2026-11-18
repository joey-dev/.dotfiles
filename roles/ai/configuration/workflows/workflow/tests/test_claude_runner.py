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


def _make_sandbox(tmp_path: Path, *, flake_dir: Path | None = None) -> SandboxSpec:
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
        flake_dir=flake_dir,
    )


def test_headless_builds_expected_claude_flags(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    fake_home = tmp_path / "host_home"
    fake_home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: fake_home)

    captured: list[list[str]] = []

    def fake_run(cmd: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        captured.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, stdout="ok", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    mcp = tmp_path / "mcp.json"
    mcp.write_text("{}", encoding="utf-8")
    flake_dir = tmp_path / "flake"
    flake_dir.mkdir()

    stage = StageConfig(
        name=StageName.INTAKE,
        model="sonnet",
        thinking="medium",
        repo_access=RepoAccess.NONE,
        allow_network=True,
        mcp_config=mcp,
        allowed_tools=("Read", "Write"),
    )
    sandbox = SandboxSpec(
        repo_dir=None,
        repo_access=RepoAccess.NONE,
        state_dir=tmp_path / "state",
        skills_dirs=(),
        kb_dir=None,
        allow_network=False,
        workdir=tmp_path / "state",
        mcp_config=mcp,
        flake_dir=flake_dir,
    )
    (tmp_path / "state").mkdir(exist_ok=True)

    res = run_claude_headless(stage, sandbox, "fetch ticket")

    assert res.returncode == 0
    assert res.stdout == "ok"
    cmd = captured[0]
    assert cmd[:4] == ["nix", "develop", str(flake_dir), "--command"]
    assert "--unshare-net" in cmd
    assert "--unshare-pid" in cmd
    assert "/tmp/cw-proxy.sock" in cmd
    inner = cmd[cmd.index("--") + 1 :]
    claude_args = inner[inner.index("claude") :]
    assert claude_args[0] == "claude"
    assert "-p" in claude_args
    assert "fetch ticket" in claude_args
    assert "--model" in claude_args
    assert "sonnet" in claude_args
    assert "--permission-mode" in claude_args
    assert "dontAsk" in claude_args
    assert claude_args[claude_args.index("--effort") + 1] == "medium"
    assert claude_args[claude_args.index("--tools") + 1] == "Read,Write"
    assert "--strict-mcp-config" in claude_args
    assert "--add-dir" in claude_args
    assert str(fake_home / "notes") in claude_args
    assert str(fake_home / "flake") in claude_args
    assert "--allowedTools" in claude_args
    assert "Read,Write" in claude_args
    assert "--mcp-config" in claude_args
    assert str(fake_home / ".claude" / "mcp.json") in claude_args


def test_interactive_uses_session_id_or_resume(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    fake_home = tmp_path / "host_home"
    fake_home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: fake_home)

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
    claude1 = inner1[inner1.index("claude") :]
    claude2 = inner2[inner2.index("claude") :]
    assert claude1[1:3] == ["--session-id", "uuid-1"]
    assert claude2[1:3] == ["--resume", "uuid-1"]
