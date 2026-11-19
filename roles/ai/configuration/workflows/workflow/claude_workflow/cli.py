"""CLI entrypoint for claude-workflow."""

from __future__ import annotations

import argparse
import os
import sys
import time
from collections.abc import Callable, Sequence
from pathlib import Path

from claude_workflow.config import (
    DOTFILES_CONFIG_DIR,
    GLOBAL_FILE,
    STAGE_ORDER,
    StageName,
    check_config,
    default_config_dir,
    load_config,
    render_full_config,
    repo_config_path,
)
from claude_workflow.git_host import GitError, repo_root
from claude_workflow.pipeline import run_pipeline


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for claude-workflow."""
    parser = argparse.ArgumentParser(
        prog="claude-workflow",
        description="Crash-safe Jira-to-branch Claude Code orchestrator. "
        "'claude-workflow config check|render' checks the config.",
    )
    parser.add_argument("ticket", help="Jira ticket ID (e.g. PROJ-123)")
    stages = parser.add_mutually_exclusive_group()
    stages.add_argument(
        "--from-stage",
        choices=[s.value for s in STAGE_ORDER],
        default=None,
        help="Re-run a stage and continue through the remaining stages",
    )
    stages.add_argument(
        "--only-stage",
        choices=[s.value for s in STAGE_ORDER],
        help="Re-run one stage and stop after its approval gate",
    )
    parser.add_argument(
        "--auto",
        action="store_true",
        help="Skip approval gates (Q&A and Retro remain interactive)",
    )
    parser.add_argument(
        "--config-dir",
        type=Path,
        default=None,
        help="Folder with global.config.json and repository/ "
        "(default: $XDG_CONFIG_HOME/claude-workflow)",
    )
    return parser


def build_config_parser() -> argparse.ArgumentParser:
    """Parser for 'claude-workflow config check|render'."""
    parser = argparse.ArgumentParser(prog="claude-workflow config")
    sub = parser.add_subparsers(dest="action", required=True)
    for name, text in (
        ("check", "Validate the merged global + repo config; prints 'ok' or the errors."),
        ("render", "Write full-configs/<repo-name>.config.json (merged, read-only view)."),
    ):
        action = sub.add_parser(name, help=text, description=text)
        action.add_argument(
            "--repo", type=Path, default=Path.cwd(), help="Repository (default: current dir)"
        )
        action.add_argument("--config-dir", type=Path, default=None, help="Config source folder")
        if name == "render":
            action.add_argument(
                "--out",
                type=Path,
                default=None,
                help="Output folder (default: <config-dir>/full-configs)",
            )
            action.add_argument(
                "--watch", action="store_true", help="Re-render when a source file changes"
            )
    return parser


def _print_result(errors: list[str]) -> None:
    print("\n".join(errors) if errors else "ok", flush=True)


def watch_files(
    paths: Sequence[Path],
    on_change: Callable[[], object],
    *,
    interval: float = 1.0,
) -> None:
    """Call on_change whenever the mtime of one of paths changes (polling). Ctrl-C stops."""

    def stamps() -> list[float | None]:
        return [p.stat().st_mtime if p.exists() else None for p in paths]

    last = stamps()
    try:
        while True:
            time.sleep(interval)
            current = stamps()
            if current != last:
                last = current
                on_change()
    except KeyboardInterrupt:
        pass


def config_main(argv: Sequence[str]) -> int:
    """'claude-workflow config check|render'."""
    parser = build_config_parser()
    args = parser.parse_args(argv)
    try:
        root = repo_root(args.repo)
    except (OSError, GitError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if args.action == "check":
        errors = check_config(root, args.config_dir or default_config_dir())
        _print_result(errors)
        return 1 if errors else 0

    # render: read the editable dotfiles source by default; the XDG copy is a read-only
    # Nix store symlink and only changes on a home-manager switch.
    config_dir: Path = args.config_dir or (
        DOTFILES_CONFIG_DIR if DOTFILES_CONFIG_DIR.is_dir() else default_config_dir()
    )
    out_dir: Path | None = args.out
    if out_dir is None:
        if not os.access(config_dir, os.W_OK):
            print(f"error: {config_dir} is read-only; pass --out DIR", file=sys.stderr)
            return 1
        out_dir = config_dir / "full-configs"

    def render() -> int:
        path, errors = render_full_config(root, config_dir, out_dir)
        print(f"wrote {path}", flush=True)
        _print_result(errors)
        return 1 if errors else 0

    code = render()
    if args.watch:
        sources = [config_dir / GLOBAL_FILE, repo_config_path(config_dir, root)]
        print(f"watching {', '.join(map(str, sources))} (Ctrl-C stops)", flush=True)
        watch_files(sources, render)
        return 0
    return code


def main(argv: Sequence[str] | None = None) -> int:
    """Parse CLI arguments and run the workflow pipeline (or 'config ...')."""
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv[:1] == ["config"]:
        return config_main(argv[1:])
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        # Always work on the repository root, even when started in a subfolder.
        config = load_config(repo_root(Path.cwd()), args.config_dir)
    except (OSError, ValueError, TypeError, GitError) as exc:
        parser.error(str(exc))
    from_stage = StageName(args.from_stage) if args.from_stage is not None else None
    return run_pipeline(
        ticket_id=args.ticket,
        config=config,
        from_stage=from_stage,
        auto=bool(args.auto),
        only_stage=StageName(args.only_stage) if args.only_stage is not None else None,
    )


if __name__ == "__main__":
    sys.exit(main())
