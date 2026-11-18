"""CLI entrypoint for claude-workflow."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from claude_workflow.config import STAGE_ORDER, StageName, load_config
from claude_workflow.pipeline import run_pipeline


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for claude-workflow."""
    parser = argparse.ArgumentParser(
        prog="claude-workflow",
        description="Crash-safe Jira-to-branch Claude Code orchestrator.",
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
        "--config",
        type=Path,
        default=None,
        help="Path to JSON workflow config file",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Parse CLI arguments and run the workflow pipeline."""
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        config = load_config(args.config)
    except (OSError, ValueError, TypeError) as exc:
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
