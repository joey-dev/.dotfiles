"""Tests for claude_workflow.sandbox."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import Any, cast

import pytest

import claude_workflow.sandbox as sandbox_mod
from claude_workflow.config import RepoAccess
from claude_workflow.sandbox import (
    SandboxSpec,
    build_bwrap_command,
    prepare_sandbox_home,
    sandbox_paths,
    sandbox_settings,
)


def _has_slice(args: list[str], *items: str) -> bool:
    n = len(items)
    return any(args[i : i + n] == list(items) for i in range(len(args) - n + 1))


def test_bwrap_ro_repo_and_unshare_net(tmp_path: Path, monkeypatch: Any) -> None:
    fake_home = tmp_path / "host_home"
    fake_home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: fake_home)

    repo = tmp_path / "repo"
    repo.mkdir()
    state_dir = tmp_path / "state"
    state_dir.mkdir()

    spec = SandboxSpec(
        repo_dir=repo,
        repo_access=RepoAccess.RO,
        state_dir=state_dir,
        skills_dirs=(),
        kb_dir=None,
        allow_network=False,
        workdir=repo,
    )
    cmd = build_bwrap_command(spec, ["claude", "-p", "hello"])

    assert "--unshare-net" in cmd
    assert "--unshare-pid" in cmd
    assert _has_slice(cmd, "--tmpfs", "/home")
    assert not _has_slice(cmd, "--ro-bind", "/etc", "/etc")
    assert _has_slice(cmd, "--ro-bind", str(repo), str(fake_home / "repo"))
    assert _has_slice(cmd, "--bind", str(state_dir), str(fake_home / "notes"))
    assert _has_slice(cmd, "--chdir", str(fake_home / "repo"))
    assert cmd[-4:] == ["--", "claude", "-p", "hello"]


def test_bwrap_hides_git_directory(tmp_path: Path, monkeypatch: Any) -> None:
    fake_home = tmp_path / "host_home"
    fake_home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: fake_home)

    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)
    state_dir = tmp_path / "state"
    state_dir.mkdir()

    spec = SandboxSpec(
        repo_dir=repo,
        repo_access=RepoAccess.RO,
        state_dir=state_dir,
        skills_dirs=(),
        kb_dir=None,
        allow_network=True,
        workdir=repo,
    )
    cmd = build_bwrap_command(spec, ["claude"])

    assert "--unshare-net" not in cmd
    assert _has_slice(cmd, "--tmpfs", str(fake_home / "repo" / ".git"))


def test_bwrap_hides_git_worktree_file(tmp_path: Path, monkeypatch: Any) -> None:
    fake_home = tmp_path / "host_home"
    fake_home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: fake_home)

    worktree = tmp_path / "wt"
    worktree.mkdir()
    (worktree / ".git").write_text("gitdir: /some/repo/.git/worktrees/wt\n", encoding="utf-8")
    state_dir = tmp_path / "state"
    state_dir.mkdir()

    spec = SandboxSpec(
        repo_dir=worktree,
        repo_access=RepoAccess.RW,
        state_dir=state_dir,
        skills_dirs=(),
        kb_dir=None,
        allow_network=False,
        workdir=worktree,
    )
    cmd = build_bwrap_command(spec, ["claude"])

    assert _has_slice(cmd, "--bind", str(worktree), str(fake_home / "wt"))
    assert _has_slice(cmd, "--ro-bind", "/dev/null", str(fake_home / "wt" / ".git"))
    assert not _has_slice(cmd, "--tmpfs", str(fake_home / "wt" / ".git"))


def test_bwrap_mounts_kb_and_flake_but_not_skills(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    fake_home = tmp_path / "host_home"
    fake_home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: fake_home)

    repo = tmp_path / "repo"
    repo.mkdir()
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    kb_dir = tmp_path / "kb"
    kb_dir.mkdir()
    flake_dir = tmp_path / "flake"
    flake_dir.mkdir()
    shared_skill = tmp_path / "skills" / "shared"
    explore_skill = tmp_path / "skills" / "explore"
    plan_skill = tmp_path / "skills" / "plan"
    shared_skill.mkdir(parents=True)
    explore_skill.mkdir(parents=True)
    plan_skill.mkdir(parents=True)

    spec = SandboxSpec(
        repo_dir=repo,
        repo_access=RepoAccess.RO,
        state_dir=state_dir,
        skills_dirs=(shared_skill, explore_skill),
        kb_dir=kb_dir,
        allow_network=True,
        workdir=repo,
        flake_dir=flake_dir,
    )
    cmd = build_bwrap_command(spec, ["claude"], env={})

    assert _has_slice(cmd, "--ro-bind", str(kb_dir), str(fake_home / "kb"))
    assert _has_slice(cmd, "--ro-bind", str(flake_dir), str(fake_home / "flake"))
    # Skills reach Claude as a system prompt, so they are not mounted.
    assert not any(arg.startswith(str(fake_home / ".claude" / "skills")) for arg in cmd)
    assert str(shared_skill) not in cmd


def test_prepare_sandbox_home_and_proxy_bridge(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    fake_home = tmp_path / "host_home"
    (fake_home / ".claude").mkdir(parents=True)
    (fake_home / ".claude" / ".credentials.json").write_text('{"token":"x"}', encoding="utf-8")
    (fake_home / ".claude" / "settings.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(Path, "home", lambda: fake_home)

    state_dir = tmp_path / "state"
    state_dir.mkdir()
    sandbox_home_host = prepare_sandbox_home(state_dir)
    assert (sandbox_home_host / ".claude" / ".credentials.json").read_text(encoding="utf-8") == '{"token":"x"}'

    mcp_cfg = tmp_path / "mcp.json"
    mcp_cfg.write_text("{}", encoding="utf-8")
    sock = tmp_path / "proxy.sock"
    sock.write_text("", encoding="utf-8")
    settings_file = tmp_path / "generated-settings.json"
    settings_file.write_text("{}", encoding="utf-8")

    spec = SandboxSpec(
        repo_dir=None,
        repo_access=RepoAccess.NONE,
        state_dir=state_dir,
        skills_dirs=(),
        kb_dir=None,
        allow_network=False,
        workdir=state_dir,
        mcp_config=mcp_cfg,
        proxy_socket=sock,
        settings_file=settings_file,
    )
    cmd = build_bwrap_command(spec, ["claude", "-p", "hi"])

    assert _has_slice(cmd, "--bind", str(sandbox_home_host), str(fake_home))
    assert _has_slice(
        cmd,
        "--ro-bind",
        str(settings_file),
        str(fake_home / ".claude" / "settings.json"),
    )
    assert _has_slice(cmd, "--ro-bind", str(mcp_cfg), str(fake_home / ".claude" / "mcp.json"))
    assert _has_slice(cmd, "--bind", str(sock), "/tmp/cw-proxy.sock")
    inner = cmd[cmd.index("--") + 1 :]
    assert inner[:2] == ["sh", "-c"]
    assert inner[3:] == ["cw-bridge", "claude", "-p", "hi"]


def test_bwrap_ro_binds_repo_overlays_after_repo(tmp_path: Path, monkeypatch: Any) -> None:
    fake_home = tmp_path / "host_home"
    fake_home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: fake_home)
    main_vendor = tmp_path / "main" / "vendor"
    main_vendor.mkdir(parents=True)
    tree = tmp_path / "PROJ-1"
    tree.mkdir()
    state_dir = tmp_path / "state"
    state_dir.mkdir()

    spec = SandboxSpec(
        repo_dir=tree,
        repo_access=RepoAccess.RW,
        state_dir=state_dir,
        skills_dirs=(),
        kb_dir=None,
        allow_network=False,
        workdir=tree,
        repo_ro_overlays=((main_vendor, "vendor"),),
    )
    cmd = build_bwrap_command(spec, ["true"])

    assert _has_slice(cmd, "--ro-bind", str(main_vendor), str(fake_home / "PROJ-1" / "vendor"))
    assert cmd.index(str(main_vendor)) > cmd.index(str(tree))


def test_bwrap_clears_env_and_sets_given_vars(tmp_path: Path, monkeypatch: Any) -> None:
    fake_home = tmp_path / "host_home"
    fake_home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: fake_home)
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    spec = SandboxSpec(
        repo_dir=None,
        repo_access=RepoAccess.NONE,
        state_dir=state_dir,
        skills_dirs=(),
        kb_dir=None,
        allow_network=True,
        workdir=state_dir,
    )

    cmd = build_bwrap_command(spec, ["true"], env={"TERM": "xterm"})

    assert "--clearenv" in cmd
    assert _has_slice(cmd, "--setenv", "TERM", "xterm")
    assert cmd.index("--clearenv") < cmd.index("--setenv")


def test_bwrap_does_not_pass_docker_host(tmp_path: Path, monkeypatch: Any) -> None:
    fake_home = tmp_path / "host_home"
    fake_home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: fake_home)
    monkeypatch.setenv("DOCKER_HOST", "unix:///var/lib/cw-docker-sock/docker.sock")
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    spec = SandboxSpec(
        repo_dir=None,
        repo_access=RepoAccess.NONE,
        state_dir=state_dir,
        skills_dirs=(),
        kb_dir=None,
        allow_network=True,
        workdir=state_dir,
    )

    for env in (None, {"TERM": "xterm"}):
        cmd = build_bwrap_command(spec, ["true"], env=env)
        assert "--clearenv" in cmd
        assert "DOCKER_HOST" not in cmd
        assert not any("cw-docker-sock" in arg for arg in cmd)


def _minimal_spec(tmp_path: Path) -> SandboxSpec:
    state_dir = tmp_path / "state"
    state_dir.mkdir(exist_ok=True)
    return SandboxSpec(
        repo_dir=None,
        repo_access=RepoAccess.NONE,
        state_dir=state_dir,
        skills_dirs=(),
        kb_dir=None,
        allow_network=True,
        workdir=state_dir,
    )


def test_interactive_omits_new_session_when_tiocsti_disabled(
    tmp_path: Path, monkeypatch: Any
) -> None:
    monkeypatch.setattr(sandbox_mod, "tiocsti_disabled", lambda: True)

    cmd = build_bwrap_command(_minimal_spec(tmp_path), ["true"], env={}, interactive=True)

    assert "--new-session" not in cmd


def test_interactive_keeps_new_session_when_tiocsti_enabled(
    tmp_path: Path, monkeypatch: Any
) -> None:
    monkeypatch.setattr(sandbox_mod, "tiocsti_disabled", lambda: False)

    cmd = build_bwrap_command(_minimal_spec(tmp_path), ["true"], env={}, interactive=True)

    assert "--new-session" in cmd


def test_headless_keeps_new_session(tmp_path: Path, monkeypatch: Any) -> None:
    monkeypatch.setattr(sandbox_mod, "tiocsti_disabled", lambda: True)

    cmd = build_bwrap_command(_minimal_spec(tmp_path), ["true"], env={})

    assert "--new-session" in cmd


def test_sandbox_settings_drops_hooks(tmp_path: Path) -> None:
    host = tmp_path / "settings.json"
    host.write_text(
        json.dumps({"hooks": {"Stop": []}, "permissions": {"deny": ["Read(~/.ssh/**)"]}})
    )

    settings = sandbox_settings(host)

    assert "hooks" not in settings
    assert settings["permissions"] == {
        "deny": ["Read(~/.ssh/**)", "Read(**/.env)", "Read(**/.env.*)"]
    }


def test_home_ro_mounts_are_read_only_and_readable(tmp_path: Path, monkeypatch: Any) -> None:
    fake_home = tmp_path / "host_home"
    fake_home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: fake_home)
    claude_md = tmp_path / "CLAUDE.md"
    claude_md.write_text("# me")
    skills = tmp_path / "skills"
    skills.mkdir()
    spec = replace(
        _minimal_spec(tmp_path),
        home_ro_mounts=((claude_md, ".claude/CLAUDE.md"), (skills, "skills")),
    )

    cmd = build_bwrap_command(spec, ["true"], env={})

    assert _has_slice(cmd, "--ro-bind", str(claude_md), str(fake_home / ".claude" / "CLAUDE.md"))
    assert _has_slice(cmd, "--ro-bind", str(skills), str(fake_home / "skills"))
    assert fake_home / "skills" in sandbox_paths(spec).add_dirs


def _token(expires_at: int) -> str:
    return json.dumps({"claudeAiOauth": {"accessToken": f"t{expires_at}", "expiresAt": expires_at}})


def _creds_setup(tmp_path: Path, monkeypatch: Any) -> tuple[Path, Path, Path]:
    fake_home = tmp_path / "host_home"
    (fake_home / ".claude").mkdir(parents=True)
    monkeypatch.setattr(Path, "home", lambda: fake_home)
    host = fake_home / ".claude" / ".credentials.json"
    host.write_text(_token(100))
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    sandbox = prepare_sandbox_home(state_dir) / ".claude" / ".credentials.json"
    return host, sandbox, state_dir


def test_host_token_that_expires_later_is_copied_in(tmp_path: Path, monkeypatch: Any) -> None:
    host, sandbox, state_dir = _creds_setup(tmp_path, monkeypatch)
    host.write_text(_token(200))

    prepare_sandbox_home(state_dir)

    assert sandbox.read_text() == _token(200)
    assert sandbox.stat().st_mode & 0o777 == 0o600


def test_newer_sandbox_token_is_kept_and_host_untouched(tmp_path: Path, monkeypatch: Any) -> None:
    host, sandbox, state_dir = _creds_setup(tmp_path, monkeypatch)
    sandbox.write_text(_token(300))

    prepare_sandbox_home(state_dir)

    assert sandbox.read_text() == _token(300)
    assert host.read_text() == _token(100)


def test_credentials_copy_never_follows_planted_symlink(tmp_path: Path, monkeypatch: Any) -> None:
    # A sandbox could plant a symlink where a fixed temp name would be.
    _host, sandbox, state_dir = _creds_setup(tmp_path, monkeypatch)
    victim = tmp_path / "victim.txt"
    victim.write_text("keep me")
    victim.chmod(0o644)
    for name in (".credentials.json.tmp", "..credentials.json.tmp"):
        (sandbox.parent / name).symlink_to(victim)
    sandbox.unlink()

    prepare_sandbox_home(state_dir)

    assert victim.read_text() == "keep me"
    assert victim.stat().st_mode & 0o777 == 0o644
    assert not sandbox.is_symlink()
    assert sandbox.read_text() == _token(100)


def test_symlinked_sandbox_claude_dir_is_refused(tmp_path: Path, monkeypatch: Any) -> None:
    _host, sandbox, state_dir = _creds_setup(tmp_path, monkeypatch)
    claude_dir = sandbox.parent
    for child in claude_dir.iterdir():
        child.unlink()
    claude_dir.rmdir()
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    claude_dir.symlink_to(elsewhere)

    with pytest.raises(RuntimeError, match="symlink"):
        prepare_sandbox_home(state_dir)


def test_repo_masks_hide_folder_with_tmpfs(tmp_path: Path, monkeypatch: Any) -> None:
    fake_home = tmp_path / "host_home"
    fake_home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: fake_home)
    tree = tmp_path / "PROJ-1"
    (tree / "nginx-proxy" / "certs").mkdir(parents=True)
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    spec = SandboxSpec(
        repo_dir=tree,
        repo_access=RepoAccess.RW,
        state_dir=state_dir,
        skills_dirs=(),
        kb_dir=None,
        allow_network=False,
        workdir=tree,
        repo_masks=("nginx-proxy/certs", "absent", "../escape"),
    )

    cmd = build_bwrap_command(spec, ["true"])

    masked = str(fake_home / "PROJ-1" / "nginx-proxy" / "certs")
    assert _has_slice(cmd, "--tmpfs", masked)
    assert cmd.index(masked) > cmd.index(str(tree))
    assert str(fake_home / "PROJ-1" / "absent") not in cmd
    assert not any("escape" in arg for arg in cmd)


def test_cache_dir_is_bound_and_sets_tmpdir(tmp_path: Path, monkeypatch: Any) -> None:
    fake_home = tmp_path / "host_home"
    fake_home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: fake_home)
    cache = tmp_path / "cache"
    cache.mkdir()
    spec = replace(_minimal_spec(tmp_path), cache_dir=cache)

    cmd = build_bwrap_command(spec, ["true"], env={"TMPDIR": "/host/tmp"})

    assert _has_slice(cmd, "--bind", str(cache), "/tmp/cw-cache")
    tmp_index = next(i for i in range(len(cmd) - 1) if cmd[i : i + 2] == ["--tmpfs", "/tmp"])
    assert cmd.index(str(cache)) > tmp_index
    assert _has_slice(cmd, "--setenv", "TMPDIR", "/tmp/cw-cache")
    last_tmpdir = max(i for i, arg in enumerate(cmd) if arg == "TMPDIR")
    assert cmd[last_tmpdir + 1] == "/tmp/cw-cache"


def test_no_cache_dir_means_no_cache_mount(tmp_path: Path, monkeypatch: Any) -> None:
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    cmd = build_bwrap_command(_minimal_spec(tmp_path), ["true"], env={})

    assert "/tmp/cw-cache" not in cmd


def test_sandbox_settings_deny_env_files_merged_with_host_denies(tmp_path: Path) -> None:
    host = tmp_path / "settings.json"
    host.write_text(json.dumps({"permissions": {"deny": ["Read(~/.ssh/**)"], "allow": ["x"]}}))

    permissions = cast(dict[str, Any], sandbox_settings(host)["permissions"])

    assert permissions["deny"] == ["Read(~/.ssh/**)", "Read(**/.env)", "Read(**/.env.*)"]
    assert permissions["allow"] == ["x"]


def test_sandbox_settings_without_host_file_still_denies_env(tmp_path: Path) -> None:
    settings = sandbox_settings(tmp_path / "absent.json")

    assert settings == {"permissions": {"deny": ["Read(**/.env)", "Read(**/.env.*)"]}}
