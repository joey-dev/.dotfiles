"""Stage 6: Verify — run the fixed checks and the ticket's tests.txt on the worktree.

`flake:` lines and verify_commands run in the no-network sandbox. `docker:` lines run
on the host through the compose stack, but only after the Docker guard passed.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory

from claude_workflow.config import DockerConfig, StageName
from claude_workflow.docker_stack import (
    base_runner_copy,
    compose_env,
    guard_patterns,
    guard_violations,
    prepare_worktree,
    run_command,
    runner_command,
    up_command,
)
from claude_workflow.env import sandbox_env
from claude_workflow.git_host import (
    GitError,
    capture_diff,
    changed_files,
    changed_paths,
    diff_digest,
)
from claude_workflow.sandbox import build_bwrap_command, sandbox_paths
from claude_workflow.stages.base import (
    StageContext,
    StageOutcome,
    StageResult,
    build_stage_sandbox,
    read_artifact,
    write_artifact,
)
from claude_workflow.tests_file import TESTS_FILE, parse_tests_file

CHANGED_FILES = "changed-files.txt"


def _section(label: str, status: str, output: str) -> str:
    """One artifact section: always the status and the full output."""
    return f"## `{label}` — {status}\n\n```text\n{output}\n```\n"


# Extra seconds for `up` to build images before `--wait-timeout` starts counting.
UP_BUILD_HEADROOM = 600


class _DockerStop(Exception):
    """Docker tests cannot run safely or at all; the human decides (NEEDS_HUMAN)."""

    def __init__(self, reason: str, sections: list[str]) -> None:
        super().__init__(f"Docker tests skipped: {reason}")
        self.sections = [*sections, f"## Docker tests skipped\n\n{reason}\n"]


def _run_sandbox_checks(
    ctx: StageContext, workdir: Path, flake_lines: list[str], changed: list[str]
) -> tuple[list[str], bool]:
    """Run verify_commands, then flake: lines, in the no-network sandbox (env built once).

    Only the trusted verify_commands get the persistent Verify cache. flake: lines come
    from tests.txt, which Implement controls, so they get a fresh /tmp instead.
    """
    sandbox = build_stage_sandbox(
        ctx, StageName.VERIFY, repo_dir=workdir, kb_dir=None, workdir=workdir
    )
    sections: list[str] = []
    all_passed = True
    with TemporaryDirectory(prefix="cw-verify-") as scratch:
        sandbox = replace(sandbox, state_dir=Path(scratch), skills_dirs=(), mcp_config=None)
        listing = "".join(f"{path}\n" for path in changed)
        (Path(scratch) / CHANGED_FILES).write_text(listing, encoding="utf-8")
        flake = sandbox.flake_dir if sandbox.flake_dir and sandbox.flake_dir.exists() else None
        env = sandbox_env(flake)
        env["CW_CHANGED_FILES"] = str(sandbox_paths(sandbox).notes_dir / CHANGED_FILES)
        untrusted = replace(sandbox, cache_dir=None)
        commands = [(cmd, cmd, sandbox) for cmd in ctx.config.verify_commands]
        commands += [(f"flake: {line}", line, untrusted) for line in flake_lines]
        for label, cmd, spec in commands:
            argv = build_bwrap_command(spec, ["sh", "-c", cmd], env=env)
            status, output = run_command(
                argv, cwd=None, env=None, timeout=ctx.config.verify_timeout
            )
            all_passed = all_passed and status == "PASS"
            sections.append(_section(label, status, output))
    return sections, all_passed


def _check_guard(
    cfg: DockerConfig, workdir: Path, base: str, patterns: tuple[str, ...], sections: list[str]
) -> None:
    """Raise _DockerStop when a protected file differs from base (or the check fails)."""
    try:
        paths = guard_violations(workdir, base, patterns, cfg.host_copies)
    except (ValueError, GitError) as exc:
        raise _DockerStop(
            f"the guard could not check the worktree ({exc}). Run them by hand.",
            sections,
        ) from exc
    if paths:
        raise _DockerStop(
            f"the diff touches {', '.join(paths)}. Run them by hand.",
            sections,
        )


def _run_docker_checks(
    ctx: StageContext, workdir: Path, base: str, lines: list[str]
) -> tuple[list[str], bool]:
    """Start the compose stack and run each docker: line on the host (raises _DockerStop)."""
    cfg = ctx.config.docker
    if cfg is None:
        output = "tests.txt has docker: lines, but the workflow config has no docker section."
        return [_section("docker", "FAIL (Docker not configured)", output)], False
    with TemporaryDirectory(prefix="cw-runner-") as runner_dir:
        return _run_docker_stack(ctx, cfg, workdir, base, lines, Path(runner_dir))


def _run_docker_stack(
    ctx: StageContext, cfg: DockerConfig, workdir: Path, base: str, lines: list[str],
    runner_dir: Path,
) -> tuple[list[str], bool]:
    """Guard, prepare, `up`, then run each line with the base commit's runner copy."""
    runner = runner_dir / Path(cfg.test_runner).name
    sections: list[str] = []
    runs: list[tuple[str, list[str]]] = []
    for line in lines:
        try:
            runs.append((line, runner_command(cfg, runner, line)))
        except ValueError as exc:
            sections.append(_section(f"docker: {line}", "FAIL (invalid line)", str(exc)))
    if not runs:
        return sections, False

    repo = ctx.config.repo_path
    patterns = guard_patterns(cfg)
    _check_guard(cfg, workdir, base, patterns, sections)
    try:
        base_runner_copy(cfg, workdir, base, runner_dir)
        prepare_worktree(cfg, workdir, repo)
    except (ValueError, OSError) as exc:  # OSError: e.g. unreadable or odd host files
        raise _DockerStop(f"preparing the worktree failed: {exc}", sections) from exc
    env = compose_env(cfg, workdir, repo)
    status, output = run_command(
        up_command(cfg, workdir, repo),
        cwd=workdir,
        env=env,
        timeout=cfg.up_timeout + UP_BUILD_HEADROOM,
    )
    sections.append(_section("docker compose up", status, output))
    all_passed = status == "PASS" and len(runs) == len(lines)
    if status != "PASS":
        return sections, False
    for line, argv in runs:
        # The stack runs worktree code that could rewrite the compose file: check again.
        _check_guard(cfg, workdir, base, patterns, sections)
        status, output = run_command(
            argv, cwd=workdir, env=env, timeout=ctx.config.verify_timeout
        )
        all_passed = all_passed and status == "PASS"
        sections.append(_section(f"docker: {line}", status, output))
    return sections, all_passed


class VerifyStage:
    """Run verify_commands and tests.txt, and write 06-verify.md."""

    def run(self, ctx: StageContext) -> StageResult:
        """Run the checks, record every result, and decide the outcome.

        DONE / NEEDS_FIX / FAILED, or NEEDS_HUMAN when the Docker tests had to stop.
        """
        workdir = ctx.state.worktree_path
        base = ctx.state.base_commit
        artifact = ctx.state_dir / "06-verify.md"
        if workdir is None or not workdir.is_dir() or not base:
            message = "Verification requires a worktree and base."
            return StageResult(StageOutcome.FAILED, None, message)
        before = capture_diff(workdir, base)

        tests_path = ctx.state_dir / TESTS_FILE
        if tests_path.is_symlink() or not tests_path.is_file():
            write_artifact(artifact, f"# Verification\n\nNo {TESTS_FILE} found.\n")
            ctx.state.verified_diff = diff_digest(before)
            return StageResult(
                StageOutcome.NEEDS_FIX, artifact, f"write {TESTS_FILE} (see 04-plan.md)"
            )
        lines, errors = parse_tests_file(read_artifact(tests_path))
        sections = ["# Verification\n"]
        if not lines and not errors:
            sections.append(f"Note: {TESTS_FILE} lists no tests.\n")
        sections += [_section(TESTS_FILE, "FAIL (invalid line)", error) for error in errors]

        flake_lines = [t.text for t in lines if t.kind == "flake"]
        changed = changed_paths(workdir, base)
        found, all_passed = _run_sandbox_checks(ctx, workdir, flake_lines, changed)
        sections += found
        stop: str | None = None
        docker_lines = [t.text for t in lines if t.kind == "docker"]
        if docker_lines:  # no docker: lines → never start the stack
            try:
                found, docker_passed = _run_docker_checks(ctx, workdir, base, docker_lines)
            except _DockerStop as exc:
                found, docker_passed, stop = exc.sections, False, str(exc)
            sections += found
            all_passed = all_passed and docker_passed
        all_passed = all_passed and not errors

        write_artifact(artifact, "\n".join(sections))
        after = capture_diff(workdir, base)
        if after != before:
            files = ", ".join(changed_files(before, after)) or "unknown files"
            return StageResult(
                StageOutcome.FAILED,
                artifact,
                f"Verification changed the worktree diff: {files}. "
                "Add generated files to .gitignore.",
            )
        # Remember what was checked, also on failure, so "continue anyway" can go on.
        ctx.state.verified_diff = diff_digest(before)
        if stop is not None:
            return StageResult(StageOutcome.NEEDS_HUMAN, artifact, stop)
        if not all_passed:
            return StageResult(
                StageOutcome.NEEDS_FIX, artifact, f"verification failed; see {artifact}"
            )
        return StageResult(StageOutcome.DONE, artifact, "verify completed")
