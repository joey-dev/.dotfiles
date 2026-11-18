"""Claude Code CLI invocation wrapped in bwrap sandboxing and optional nix develop."""

from __future__ import annotations

import subprocess
from contextlib import nullcontext
from dataclasses import dataclass, replace

from claude_workflow.config import StageConfig
from claude_workflow.net_proxy import DEFAULT_ALLOWED_HOSTS, ConnectAllowlistProxy
from claude_workflow.sandbox import (
    SandboxSpec,
    build_bwrap_command,
    prepare_sandbox_home,
    sandbox_paths,
)


@dataclass(frozen=True)
class ClaudeResult:
    """Result of a headless Claude Code CLI invocation."""

    returncode: int
    stdout: str
    stderr: str
    session_id: str | None


def _common_claude_flags(stage: StageConfig, sandbox: SandboxSpec) -> list[str]:
    paths = sandbox_paths(sandbox)
    flags: list[str] = [
        "--model",
        stage.model,
        "--effort",
        stage.thinking,
        "--permission-mode",
        "dontAsk",
        "--tools",
        ",".join(tool for tool in stage.allowed_tools if not tool.startswith("mcp__")),
    ]
    for extra_dir in paths.add_dirs:
        flags.extend(["--add-dir", str(extra_dir)])
    if stage.allowed_tools:
        flags.extend(["--allowedTools", ",".join(stage.allowed_tools)])
    if paths.mcp_config is not None:
        flags.extend(["--mcp-config", str(paths.mcp_config)])
    if paths.mcp_config is not None or not any(
        tool.startswith("mcp__") for tool in stage.allowed_tools
    ):
        flags.append("--strict-mcp-config")
    return flags


def _proxy_context(
    sandbox: SandboxSpec,
    allowed_hosts: tuple[str, ...],
) -> ConnectAllowlistProxy | nullcontext[None]:
    if not sandbox.allow_network:
        return ConnectAllowlistProxy(allowed_hosts=allowed_hosts)
    return nullcontext(None)


def _wrap_with_flake(sandbox: SandboxSpec, bwrap_cmd: list[str]) -> list[str]:
    if sandbox.flake_dir is not None and sandbox.flake_dir.exists():
        return ["nix", "develop", str(sandbox.flake_dir), "--command", *bwrap_cmd]
    return bwrap_cmd


def run_claude_headless(
    stage: StageConfig,
    sandbox: SandboxSpec,
    prompt: str,
    session_id: str | None = None,
    allowed_proxy_hosts: tuple[str, ...] = DEFAULT_ALLOWED_HOSTS,
) -> ClaudeResult:
    """Run Claude Code non-interactively (-p) inside bwrap and capture output."""
    prepare_sandbox_home(sandbox.state_dir)
    claude_cmd: list[str] = ["claude", "-p", prompt, *_common_claude_flags(stage, sandbox)]
    if session_id is not None:
        claude_cmd.extend(["--session-id", session_id])

    with _proxy_context(sandbox, allowed_proxy_hosts) as proxy:
        effective_sandbox = (
            replace(sandbox, proxy_socket=proxy.socket_path)
            if proxy is not None
            else sandbox
        )
        bwrap_cmd = build_bwrap_command(effective_sandbox, claude_cmd)
        full_cmd = _wrap_with_flake(effective_sandbox, bwrap_cmd)
        proc = subprocess.run(full_cmd, check=False, capture_output=True, text=True)

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
    allowed_proxy_hosts: tuple[str, ...] = DEFAULT_ALLOWED_HOSTS,
) -> int:
    """Run Claude Code interactively inside bwrap, inheriting terminal stdio."""
    prepare_sandbox_home(sandbox.state_dir)
    session_flag = "--resume" if resume else "--session-id"
    claude_cmd: list[str] = [
        "claude",
        session_flag,
        session_id,
        *_common_claude_flags(stage, sandbox),
    ]
    if prompt:
        claude_cmd.append(prompt)

    with _proxy_context(sandbox, allowed_proxy_hosts) as proxy:
        effective_sandbox = (
            replace(sandbox, proxy_socket=proxy.socket_path)
            if proxy is not None
            else sandbox
        )
        bwrap_cmd = build_bwrap_command(effective_sandbox, claude_cmd)
        full_cmd = _wrap_with_flake(effective_sandbox, bwrap_cmd)
        proc = subprocess.run(full_cmd, check=False)

    return proc.returncode
