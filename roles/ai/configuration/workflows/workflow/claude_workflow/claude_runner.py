"""Claude Code CLI invocation wrapped in bwrap sandboxing."""

from __future__ import annotations

import json
import re
import subprocess
from collections.abc import Generator, Sequence
from contextlib import contextmanager, nullcontext
from dataclasses import dataclass, replace
from pathlib import Path
from tempfile import TemporaryDirectory

from claude_workflow.config import StageConfig
from claude_workflow.net_proxy import DEFAULT_ALLOWED_HOSTS, ConnectAllowlistProxy
from claude_workflow.sandbox import (
    SandboxSpec,
    build_bwrap_command,
    copy_mcp_auth_in,
    prepare_sandbox_home,
    sandbox_paths,
    sandbox_settings,
)

_FRONT_MATTER = re.compile(r"\A---\n.*?\n---\n", re.DOTALL)


@dataclass(frozen=True)
class ClaudeResult:
    """Result of a headless Claude Code CLI invocation."""

    returncode: int
    stdout: str
    stderr: str
    session_id: str | None


def skills_system_prompt(skill_dirs: Sequence[Path]) -> str:
    """Join the SKILL.md files of these folders, without their YAML front matter."""
    parts: list[str] = []
    for folder in skill_dirs:
        skill_file = folder / "SKILL.md"
        if skill_file.is_file():
            text = _FRONT_MATTER.sub("", skill_file.read_text(encoding="utf-8"))
            parts.append(text.strip())
    return "\n\n".join(parts)


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
    system_prompt = skills_system_prompt(sandbox.skills_dirs)
    if system_prompt:
        flags.extend(["--append-system-prompt", system_prompt])
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
        # The log shows which hosts were blocked, e.g. when a login refresh fails.
        log_path = sandbox.state_dir / "proxy.log"
        return ConnectAllowlistProxy(allowed_hosts=allowed_hosts, log_path=log_path)
    return nullcontext(None)


@contextmanager
def _sandboxed_command(
    sandbox: SandboxSpec,
    claude_cmd: list[str],
    allowed_hosts: tuple[str, ...],
    *,
    interactive: bool,
) -> Generator[list[str], None, None]:
    """Yield the full bwrap command line; proxy and settings file live while it runs."""
    prepare_sandbox_home(sandbox.state_dir)
    if sandbox.mcp_config is not None:
        copy_mcp_auth_in(sandbox.state_dir)  # login for mcp-remote servers
    with (
        TemporaryDirectory(prefix="cw-settings-") as settings_dir,
        _proxy_context(sandbox, allowed_hosts) as proxy,
    ):
        yield _bwrap_for(sandbox, claude_cmd, Path(settings_dir), proxy, interactive)


def _bwrap_for(
    sandbox: SandboxSpec,
    claude_cmd: list[str],
    settings_dir: Path,
    proxy: ConnectAllowlistProxy | None,
    interactive: bool,
) -> list[str]:
    """Write the sandbox settings file and build the bwrap command line."""
    # Written outside the state dir, because Claude can write there.
    settings_file = settings_dir / "settings.json"
    host_settings = Path.home() / ".claude" / "settings.json"
    settings_file.write_text(json.dumps(sandbox_settings(host_settings)), encoding="utf-8")

    effective = replace(sandbox, settings_file=settings_file)
    if proxy is not None:
        effective = replace(effective, proxy_socket=proxy.socket_path)
    return build_bwrap_command(effective, claude_cmd, interactive=interactive)


def run_claude_headless(
    stage: StageConfig,
    sandbox: SandboxSpec,
    prompt: str,
    session_id: str | None = None,
    allowed_proxy_hosts: tuple[str, ...] = DEFAULT_ALLOWED_HOSTS,
    timeout: int | None = None,
) -> ClaudeResult:
    """Run Claude Code non-interactively (-p) inside bwrap and capture output.

    On timeout the result has return code 124 (like the `timeout` command).
    """
    claude_cmd: list[str] = ["claude", "-p", prompt, *_common_claude_flags(stage, sandbox)]
    if session_id is not None:
        claude_cmd.extend(["--session-id", session_id])

    with _sandboxed_command(
        sandbox, claude_cmd, allowed_proxy_hosts, interactive=False
    ) as bwrap_cmd:
        try:
            proc = subprocess.run(
                bwrap_cmd, check=False, capture_output=True, text=True, timeout=timeout
            )
        except subprocess.TimeoutExpired:
            return ClaudeResult(124, "", f"timed out after {timeout}s", session_id)

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
    session_flag = "--resume" if resume else "--session-id"
    claude_cmd: list[str] = [
        "claude",
        session_flag,
        session_id,
        *_common_claude_flags(stage, sandbox),
    ]
    if prompt:
        claude_cmd.append(prompt)

    with _sandboxed_command(
        sandbox, claude_cmd, allowed_proxy_hosts, interactive=True
    ) as bwrap_cmd:
        proc = subprocess.run(bwrap_cmd, check=False)

    return proc.returncode
