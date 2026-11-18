"""The sandbox gets a clean environment, plus the project's dev shell."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

import pytest

import claude_workflow.env as env_mod
from claude_workflow.env import HOST_ENV_ALLOWLIST, dev_shell_env, sandbox_env


@pytest.fixture(autouse=True)
def clear_dev_shell_cache() -> None:
    dev_shell_env.cache_clear()


def _fake_nix(env_file: str, returncode: int = 0, stdout: str = "") -> Any:
    """Fake `nix develop`: writes env_file to the path given as the last argument."""
    calls: list[list[str]] = []

    def run(cmd: list[str], **_: Any) -> subprocess.CompletedProcess[str]:
        calls.append(cmd)
        target = Path(cmd[-1])
        # Only write to a real temp file path, never to e.g. "-0" in the working dir.
        if returncode == 0 and target.is_absolute():
            target.write_text(env_file)
        return subprocess.CompletedProcess(cmd, returncode, stdout=stdout, stderr="flake broke")

    run.calls = calls  # type: ignore[attr-defined]
    return run


def test_sandbox_env_drops_unlisted_host_vars(monkeypatch: Any) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "secret")
    monkeypatch.setenv("TERM", "xterm")

    env = sandbox_env(None)

    assert "GITHUB_TOKEN" not in env
    assert env["TERM"] == "xterm"


def test_allowlist_has_locale_and_terminfo() -> None:
    for name in ("LOCALE_ARCHIVE", "TERMINFO", "TERMINFO_DIRS"):
        assert name in HOST_ENV_ALLOWLIST


def test_dev_shell_runs_nix_with_ignore_environment(monkeypatch: Any, tmp_path: Path) -> None:
    fake = _fake_nix("A=1\0")
    monkeypatch.setattr(env_mod.subprocess, "run", fake)

    dev_shell_env(tmp_path)
    dev_shell_env(tmp_path)

    assert len(fake.calls) == 1
    assert fake.calls[0][:3] == ["nix", "develop", str(tmp_path)]
    assert "--ignore-environment" in fake.calls[0]


def test_dev_shell_ignores_shell_hook_banner(monkeypatch: Any, tmp_path: Path) -> None:
    banner = "== welcome ==\nSHELL=fake\0"
    monkeypatch.setattr(env_mod.subprocess, "run", _fake_nix("A=1\0B=2\0", stdout=banner))

    assert dev_shell_env(tmp_path) == {"A": "1", "B": "2"}


def test_dev_shell_skips_invalid_names_and_temp_dirs(monkeypatch: Any, tmp_path: Path) -> None:
    content = "=x\0bad name=1\0TMPDIR=/tmp/nix-shell.1\0OK=1\0"
    monkeypatch.setattr(env_mod.subprocess, "run", _fake_nix(content))

    assert dev_shell_env(tmp_path) == {"OK": "1"}


def test_dev_shell_failure_raises(monkeypatch: Any, tmp_path: Path) -> None:
    monkeypatch.setattr(env_mod.subprocess, "run", _fake_nix("", returncode=1))

    with pytest.raises(RuntimeError, match="nix develop"):
        dev_shell_env(tmp_path)


def test_dev_shell_vars_kept_even_when_host_has_same_value(
    monkeypatch: Any, tmp_path: Path
) -> None:
    # E.g. started inside a direnv shell of the same flake.
    monkeypatch.setenv("PHP_INI_SCAN_DIR", "/x")
    monkeypatch.setattr(env_mod.subprocess, "run", _fake_nix("PHP_INI_SCAN_DIR=/x\0"))

    assert sandbox_env(tmp_path)["PHP_INI_SCAN_DIR"] == "/x"


def test_path_is_dev_shell_first_then_host(monkeypatch: Any, tmp_path: Path) -> None:
    monkeypatch.setenv("PATH", "/usr/bin:/nix/store/php/bin")
    content = "PATH=/nix/store/php/bin:/no-such-path\0"
    monkeypatch.setattr(env_mod.subprocess, "run", _fake_nix(content))

    assert sandbox_env(tmp_path)["PATH"] == "/nix/store/php/bin:/usr/bin"
