"""Tests for claude_workflow.sandbox."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from claude_workflow.config import RepoAccess
from claude_workflow.sandbox import SandboxSpec, build_bwrap_command, prepare_sandbox_home


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


def test_bwrap_mounts_only_stage_skills_kb_and_flake(
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
    cmd = build_bwrap_command(spec, ["claude"])

    assert _has_slice(cmd, "--ro-bind", str(kb_dir), str(fake_home / "kb"))
    assert _has_slice(cmd, "--ro-bind", str(flake_dir), str(fake_home / "flake"))
    assert _has_slice(
        cmd,
        "--ro-bind",
        str(shared_skill),
        str(fake_home / ".claude" / "skills" / "shared"),
    )
    assert _has_slice(
        cmd,
        "--ro-bind",
        str(explore_skill),
        str(fake_home / ".claude" / "skills" / "explore"),
    )
    assert str(plan_skill) not in cmd


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
    )
    cmd = build_bwrap_command(spec, ["claude", "-p", "hi"])

    assert _has_slice(cmd, "--bind", str(sandbox_home_host), str(fake_home))
    assert _has_slice(
        cmd,
        "--ro-bind",
        str(fake_home / ".claude" / "settings.json"),
        str(fake_home / ".claude" / "settings.json"),
    )
    assert _has_slice(cmd, "--ro-bind", str(mcp_cfg), str(fake_home / ".claude" / "mcp.json"))
    assert _has_slice(cmd, "--bind", str(sock), "/tmp/cw-proxy.sock")
    inner = cmd[cmd.index("--") + 1 :]
    assert inner[:2] == ["sh", "-c"]
    assert inner[3:] == ["cw-bridge", "claude", "-p", "hi"]
