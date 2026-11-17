"""Claude Code CLI invocation wrapped in bwrap sandboxing."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass

from claude_workflow.config import StageConfig
from claude_workflow.sandbox import SandboxSpec, build_bwrap_command


@dataclass(frozen=True)
class ClaudeResult:
    """Result of a headless Claude Code CLI invocation."""

    returncode: int
    stdout: str
    stderr: str
    session_id: str | None


def _common_claude_flags(stage: StageConfig) -> list[str]:
    flags: list[str] = ["--model", stage.model]
    if stage.allowed_tools:
        flags.extend(["--allowedTools", ",".join(stage.allowed_tools)])
    if stage.mcp_config is not None:
        flags.extend(["--mcp-config", str(stage.mcp_config)])
    return flags


def run_claude_headless(
    stage: StageConfig,
    sandbox: SandboxSpec,
    prompt: str,
    session_id: str | None = None,
) -> ClaudeResult:
    """Run Claude Code non-interactively (-p) inside bwrap and capture output."""
    claude_cmd: list[str] = ["claude", "-p", prompt, *_common_claude_flags(stage)]
    if session_id is not None:
        claude_cmd.extend(["--session-id", session_id])

    bwrap_cmd = build_bwrap_command(sandbox, claude_cmd)
    proc = subprocess.run(bwrap_cmd, check=False, capture_output=True, text=True)
    return ClaudeResult(
        returncode=proc.returncode,
        stdout=proc.stdout,
        stderr=proc.stderr,
        session_id=session_id,
    )


def run_claude_interactive(
    stage: StageConfig,
    sandbox: SandboxSpec,
    prompt: str,
    session_id: str,
    resume: bool = False,
) -> int:
    """Run Claude Code interactively inside bwrap, inheriting terminal stdio."""
    session_flag = "--resume" if resume else "--session-id"
    claude_cmd: list[str] = [
        "claude",
        session_flag,
        session_id,
        *_common_claude_flags(stage),
    ]
    if prompt:
        claude_cmd.append(prompt)

    bwrap_cmd = build_bwrap_command(sandbox, claude_cmd)
    proc = subprocess.run(bwrap_cmd, check=False)
    return proc.returncode
