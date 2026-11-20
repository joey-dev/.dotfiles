"""Runners: execute a rendered command (`commands.render`) in the right place.

- `sandbox`: a fresh no-network bwrap sandbox on the worktree. Only trusted commands
  (from `verify`) get the persistent Verify cache.
- `host`: on the host, but only after the guard passed, and always the base commit's
  copy of the command's script, never the worktree file.
- `container`: `docker exec` into a running container.

Claude controls the worktree, so the host never runs worktree code outside a sandbox.
Docker access is a separate rootless daemon (`cw-docker`): Claude never gets it.
"""

from __future__ import annotations

import shlex
from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from pathlib import Path
from tempfile import TemporaryDirectory

from claude_workflow.commands import Command, host_script
from claude_workflow.config import WorkflowConfig
from claude_workflow.docker_stack import (
    UP_BUILD_HEADROOM,
    base_script_copy,
    compose_env,
    compose_model,
    docker_env,
    down_command,
    guard_patterns,
    guard_violations,
    override_path,
    port_hint,
    prepare_worktree,
    require_rootless,
    run_command,
    socket_override,
    socket_path,
    symlink_violations,
    up_command,
    write_override,
)
from claude_workflow.git_host import GitError
from claude_workflow.sandbox import SandboxSpec, build_bwrap_command, make_scratch_git


class HostStop(Exception):
    """The host may not run this safely (guard tripped, or preparing failed).

    The caller should stop and ask the human (Verify: NEEDS_HUMAN).
    """


@dataclass
class StackState:
    """Whether `docker compose up` already ran in this Verify run, and its result.

    command: the `up` command line as run (for the Verify artifact).
    """

    result: tuple[str, str] | None = None
    command: str | None = None
    override: Path | None = None


@dataclass(frozen=True)
class RunContext:
    """What the runners need for one Verify run.

    sandbox: the base spec (repo_dir = worktree, state_dir = a scratch notes folder,
    cache_dir = the Verify cache). trusted: the command comes from `verify` (not from
    tests.txt), so it may use the cache. `replace(ctx, trusted=...)` shares `stack`, so
    the compose stack still starts at most once.
    """

    config: WorkflowConfig
    worktree: Path
    base_commit: str
    sandbox: SandboxSpec
    sandbox_env: Mapping[str, str] | None = None
    trusted: bool = False
    stack: StackState = field(default_factory=StackState)


def _host_scripts(config: WorkflowConfig, cmd: Command | None = None) -> tuple[str, ...]:
    """The scripts of every host command in the config (plus cmd), for the guard.

    A malformed host command is skipped here (config check reports it, and running
    it is refused), so it can't break the other host commands.
    """
    commands = [*config.commands.values(), *([cmd] if cmd is not None else [])]
    scripts: list[str] = []
    for item in commands:
        if item.run_in != "host":
            continue
        try:
            scripts.append(host_script(item.command))
        except ValueError:
            continue
    return tuple(dict.fromkeys(scripts))


def _check_guard(ctx: RunContext, cmd: Command) -> None:
    """Raise HostStop when a protected file (or a host script) differs from base, or
    when the worktree has a symlink the base commit does not have (fail closed)."""
    docker = ctx.config.docker
    patterns = guard_patterns(docker, _host_scripts(ctx.config, cmd))
    host_copies = docker.host_copies if docker is not None else ()
    try:
        paths = guard_violations(ctx.worktree, ctx.base_commit, patterns, host_copies)
        links = symlink_violations(ctx.worktree, ctx.base_commit, host_copies)
    except (ValueError, GitError, OSError) as exc:
        raise HostStop(f"the guard could not check the worktree ({exc})") from exc
    if paths:
        raise HostStop(f"the diff touches protected files: {', '.join(paths)}")
    if links:
        raise HostStop(
            f"symlink in the worktree that is not in the base commit: {', '.join(links)}"
        )


def _subdir(root: Path, working_directory: str | None) -> Path:
    """root / working_directory; refuse absolute paths, '..' and symlinks."""
    if working_directory is None:
        return root
    rel = Path(working_directory)
    if rel.is_absolute() or ".." in rel.parts:
        raise ValueError(f"working-directory {working_directory!r} must stay in the repository")
    current = root
    for part in rel.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError(f"working-directory {working_directory!r} contains a symlink")
    return current


def _line(argv: list[str]) -> str:
    if len(argv) != 3 or argv[:2] != ["sh", "-c"]:
        raise ValueError(f"expected ['sh', '-c', line] from render, got {argv!r}")
    return argv[2]


def _docker_host(ctx: RunContext) -> str:
    """The rootless Docker socket, or HostStop with a message for the human."""
    try:
        return require_rootless(ctx.config.docker_host, ctx.config.worktree_base)
    except (ValueError, OSError, RuntimeError) as exc:
        raise HostStop(str(exc)) from exc


def _ensure_stack(ctx: RunContext, cmd: Command) -> tuple[str, str] | None:
    """Start the compose stack once per run. Returns a FAIL result if it is not up."""
    docker = ctx.config.docker
    if docker is None:
        return (
            "FAIL (no compose stack)",
            f"command {cmd.name!r} needs the compose stack, but the config has no "
            "docker-compose section.",
        )
    docker_host = _docker_host(ctx)
    if ctx.stack.result is None:
        _check_guard(ctx, cmd)
        repo = ctx.config.repo_path
        # Fresh containers each run: prepare_worktree replaces host-copy folders, and a
        # running container would keep its bind mount on the deleted folder. This also
        # clears containers left broken by an earlier failed `up`. Volumes are kept.
        down_status, down_output = run_command(
            down_command(docker, ctx.worktree, repo),
            cwd=ctx.worktree,
            env=compose_env(docker, ctx.worktree, repo, docker_host),
            timeout=docker.up_timeout,
        )
        if down_status != "PASS":
            ctx.stack.result = (down_status, down_output)
            return f"FAIL (compose stack did not start: {down_status})", down_output
        try:
            prepare_worktree(docker, ctx.worktree, repo)
        except (ValueError, OSError) as exc:  # OSError: e.g. unreadable host files
            raise HostStop(f"preparing the worktree failed: {exc}") from exc
        override = override_path(ctx.config.state_base, docker)
        try:
            model = compose_model(docker, ctx.worktree, repo, docker_host)
            write_override(override, socket_override(model, socket_path(docker_host)))
        except (ValueError, OSError) as exc:
            raise HostStop(f"could not prepare the compose override: {exc}") from exc
        ctx.stack.override = override
        up_argv = up_command(docker, ctx.worktree, repo, override)
        ctx.stack.command = shlex.join(up_argv)
        status, output = run_command(
            up_argv,
            cwd=ctx.worktree,
            env=compose_env(docker, ctx.worktree, repo, docker_host, override),
            timeout=docker.up_timeout + UP_BUILD_HEADROOM,
        )
        ctx.stack.result = (status, port_hint(output) if status != "PASS" else output)
    status, output = ctx.stack.result
    if status != "PASS":
        return f"FAIL (compose stack did not start: {status})", output
    return None


def _run_sandbox(cmd: Command, argv: list[str], ctx: RunContext) -> tuple[str, str]:
    spec = replace(
        ctx.sandbox,
        workdir=_subdir(ctx.worktree, cmd.working_directory),
        cache_dir=ctx.sandbox.cache_dir if ctx.trusted else None,
    )
    if not cmd.needs_git:
        bwrap = build_bwrap_command(spec, argv, env=ctx.sandbox_env)
        return run_command(bwrap, cwd=None, env=None, timeout=cmd.timeout)
    # Default temp dir: outside the worktree and outside the notes dir.
    with TemporaryDirectory(prefix="cw-git-") as scratch:
        spec = replace(spec, scratch_git=make_scratch_git(Path(scratch)))
        bwrap = build_bwrap_command(spec, argv, env=ctx.sandbox_env)
        return run_command(bwrap, cwd=None, env=None, timeout=cmd.timeout)


def _run_host(cmd: Command, argv: list[str], ctx: RunContext) -> tuple[str, str]:
    line = _line(argv)
    cwd = _subdir(ctx.worktree, cmd.working_directory)
    script = host_script(cmd.command)  # ValueError for make, npm, /usr/bin/x, ...
    first = cmd.command.split(maxsplit=1)[0]
    if not (line == first or line.startswith(first + " ")):
        raise ValueError(f"command {cmd.name!r}: rendered line does not start with {first!r}")
    env = None
    if cmd.needs_compose_stack:
        failed = _ensure_stack(ctx, cmd)
        if failed is not None:
            return failed
    docker = ctx.config.docker
    if docker is not None:
        env = compose_env(
            docker, ctx.worktree, ctx.config.repo_path, _docker_host(ctx), ctx.stack.override
        )
    elif ctx.config.docker_host is not None:
        env = docker_env(_docker_host(ctx))
    # Checked again right before running: the stack runs worktree code.
    _check_guard(ctx, cmd)
    with TemporaryDirectory(prefix="cw-host-") as scratch:
        try:
            copy = base_script_copy(
                ctx.worktree, ctx.base_commit, script, Path(scratch), executable=True
            )
        except (ValueError, OSError) as exc:
            raise HostStop(f"could not copy {script} from the base commit: {exc}") from exc
        line = shlex.quote(str(copy)) + line[len(first) :]
        return run_command(["sh", "-c", line], cwd=cwd, env=env, timeout=cmd.timeout)


def _run_container(cmd: Command, argv: list[str], ctx: RunContext) -> tuple[str, str]:
    line = _line(argv)
    if cmd.container is None:
        raise ValueError(f"command {cmd.name!r}: run-in 'container' needs 'container'")
    if cmd.needs_compose_stack:
        failed = _ensure_stack(ctx, cmd)
        if failed is not None:
            return failed
    host = _docker_host(ctx)
    docker_argv = [
        "docker",
        "exec",
        *(["-u", cmd.user] if cmd.user else []),
        *(["-w", cmd.working_directory] if cmd.working_directory else []),
        cmd.container,
        "sh",
        "-c",
        line,
    ]
    return run_command(docker_argv, cwd=None, env=docker_env(host), timeout=cmd.timeout)


def run(cmd: Command, argv: list[str], ctx: RunContext) -> tuple[str, str]:
    """Run one rendered command; return (status, output).

    Raises HostStop when the host may not continue safely (ask the human), and
    ValueError for a command the runner refuses (bad paths, needs-git outside sandbox).
    """
    if cmd.needs_git and cmd.run_in != "sandbox":
        raise ValueError(f"command {cmd.name!r}: needs-git only works with run-in 'sandbox'")
    if cmd.run_in == "sandbox":
        return _run_sandbox(cmd, argv, ctx)
    if cmd.run_in == "host":
        return _run_host(cmd, argv, ctx)
    return _run_container(cmd, argv, ctx)
