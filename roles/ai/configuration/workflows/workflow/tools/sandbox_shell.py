"""Debug helper: open a shell inside the same bwrap sandbox a stage would get.

Usage (from the repository you want to test against):

    python tools/sandbox_shell.py STAGE [--ticket SANDBOX-1] [--repo PATH]
        [--config-dir DIR] [--interactive] [--copy-credentials] [-- CMD ...]

- Default command is `bash`.
- Read-only stages (explore, qa, plan, review) use the ticket worktree if it
  exists, otherwise your main checkout (safe: it is mounted read-only).
- implement and verify mount the repo read-write, so they need the ticket
  worktree or an explicit --repo.
- The config is loaded for the repository you start it in (its folder name picks
  repository/<repo-name>.config.json), not for --repo, which may be a worktree.
- --interactive: build the sandbox like Q&A/Retro (keeps the terminal).
- --copy-credentials: copy your Claude login in, like a real run, so you can
  start `claude` inside.

Not part of the installed package.
"""

from __future__ import annotations

import argparse
import shlex
import subprocess
import sys
from collections.abc import Sequence
from contextlib import ExitStack
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from claude_workflow.claude_runner import _proxy_context, _sandboxed_command  # noqa: E402
from claude_workflow.config import (  # noqa: E402
    STAGE_ORDER,
    StageName,
    WorkflowConfig,
    load_config,
)
from claude_workflow.git_host import repo_root  # noqa: E402
from claude_workflow.net_proxy import DEFAULT_ALLOWED_HOSTS  # noqa: E402
from claude_workflow.sandbox import build_bwrap_command  # noqa: E402
from claude_workflow.stages.base import StageContext, build_stage_sandbox  # noqa: E402
from claude_workflow.state import load_state  # noqa: E402

READ_WRITE_STAGES = {StageName.IMPLEMENT, StageName.VERIFY}
NO_REPO_STAGES = {StageName.INTAKE, StageName.RETRO}
NO_KB_STAGES = {StageName.INTAKE, StageName.IMPLEMENT, StageName.VERIFY}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("stage", choices=[s.value for s in STAGE_ORDER])
    parser.add_argument("--ticket", default="SANDBOX-1")
    parser.add_argument("--repo", type=Path, help="Repo or worktree to mount")
    parser.add_argument(
        "--config-dir", type=Path, help="Default: $XDG_CONFIG_HOME/claude-workflow"
    )
    parser.add_argument("--interactive", action="store_true")
    parser.add_argument("--copy-credentials", action="store_true")
    parser.add_argument("cmd", nargs="*", default=["bash"])
    return parser


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    return build_parser().parse_args(argv)


def load_tool_config(args: argparse.Namespace) -> WorkflowConfig:
    """The workflow config for the repository the tool is started in."""
    return load_config(repo_root(Path.cwd()), args.config_dir)


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    config = load_tool_config(args)
    stage = StageName(args.stage)
    ticket = args.ticket.upper()
    state_dir = config.state_base / ticket
    state_dir.mkdir(parents=True, exist_ok=True)
    state = load_state(state_dir, ticket)
    ctx = StageContext(ticket, config, state, state_dir)

    # Mirror the repo/kb/workdir choices made in stages/*.py.
    repo: Path | None
    if stage in NO_REPO_STAGES:
        repo = None
    else:
        repo = args.repo or state.worktree_path
        if repo is None and stage in READ_WRITE_STAGES:
            parser.error(f"{stage.value} mounts read-write: pass --repo <worktree>")
        repo = repo or config.repo_path
    workdir = repo or state_dir
    kb = None if stage in NO_KB_STAGES else config.kb_path

    sandbox = build_stage_sandbox(ctx, stage, repo_dir=repo, kb_dir=kb, workdir=workdir)

    with ExitStack() as stack:
        if stage is StageName.VERIFY:
            # Verify: temp state dir, no skills/MCP, no proxy (fully offline).
            scratch = stack.enter_context(TemporaryDirectory(prefix="cw-verify-"))
            sandbox = replace(sandbox, state_dir=Path(scratch), skills_dirs=(), mcp_config=None)
            argv = build_bwrap_command(sandbox, args.cmd)
        elif args.copy_credentials:
            # Exactly the real path: login copied in, settings file, proxy.
            argv = stack.enter_context(
                _sandboxed_command(
                    sandbox, args.cmd, DEFAULT_ALLOWED_HOSTS, interactive=args.interactive
                )
            )
        else:
            (state_dir / "home" / ".claude").mkdir(parents=True, exist_ok=True)
            proxy = stack.enter_context(_proxy_context(sandbox, DEFAULT_ALLOWED_HOSTS))
            if proxy is not None:
                sandbox = replace(sandbox, proxy_socket=proxy.socket_path)
            argv = build_bwrap_command(sandbox, args.cmd, interactive=args.interactive)

        print("+", shlex.join(argv), file=sys.stderr)
        return subprocess.run(argv, check=False).returncode


if __name__ == "__main__":
    sys.exit(main())
