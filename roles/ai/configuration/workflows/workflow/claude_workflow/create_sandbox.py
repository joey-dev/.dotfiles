"""Run a shell, command, or Claude Code in a sandbox for the current directory."""

from __future__ import annotations

import argparse
import os
import shlex
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path
from tempfile import TemporaryDirectory, gettempdir

from claude_workflow.claude_runner import claude_flags, sandboxed_command
from claude_workflow.config import RepoAccess, StageName, default_stages
from claude_workflow.net_proxy import DEFAULT_ALLOWED_HOSTS
from claude_workflow.sandbox import SandboxSpec


def _startup(value: str) -> list[str]:
    try:
        argv = shlex.split(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc
    if not argv or not argv[0]:
        raise argparse.ArgumentTypeError("expected an executable and optional arguments")
    return argv


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="create-sandbox",
        description="Run in a Bubblewrap sandbox with write access to the current directory.",
    )
    parser.add_argument(
        "--network-access",
        choices=("false", "true"),
        required=True,
        help="false allows only the Claude HTTPS proxy; true uses the host network",
    )
    startup = parser.add_mutually_exclusive_group()
    startup.add_argument(
        "--startup", type=_startup, metavar="COMMAND",
        help="executable and shell-quoted arguments (default: $SHELL or sh)",
    )
    startup.add_argument(
        "--agent-claude", action="store_true",
        help="start Claude Code with the workflow's implementation-stage defaults",
    )
    args = parser.parse_args(argv)

    try:
        workspace = Path.cwd()
        home = Path.home()
        if home.resolve().is_relative_to(workspace):
            parser.error("run from a directory that does not contain your host home")
        if Path(gettempdir()).resolve().is_relative_to(workspace):
            parser.error("run from a directory that does not contain the host temporary directory")

        claude_md = home / ".claude" / "CLAUDE.md"
        home_mounts = ((claude_md, ".claude/CLAUDE.md"),) if claude_md.is_file() else ()
        with TemporaryDirectory(prefix="create-sandbox-") as state_dir:
            spec = SandboxSpec(
                repo_dir=workspace,
                repo_access=RepoAccess.RW,
                state_dir=Path(state_dir),
                skills_dirs=(),
                kb_dir=None,
                allow_network=args.network_access == "true",
                workdir=workspace,
                home_ro_mounts=home_mounts,
            )
            command = args.startup or [os.environ.get("SHELL") or "sh"]
            if args.agent_claude:
                stage = default_stages()[StageName.IMPLEMENT]
                command = ["claude", *claude_flags(stage, spec)]
            with sandboxed_command(
                spec, command, DEFAULT_ALLOWED_HOSTS, interactive=True
            ) as wrapped:
                returncode = subprocess.run(wrapped, check=False).returncode
                return returncode if returncode >= 0 else 128 - returncode
    except KeyboardInterrupt:
        return 130
    except (OSError, ValueError) as exc:
        print(f"create-sandbox: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
