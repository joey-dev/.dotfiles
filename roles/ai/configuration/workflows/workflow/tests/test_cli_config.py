"""Tests for `claude-workflow config check|render`."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest

from claude_workflow.cli import main

GLOBAL: dict[str, Any] = {
    "kb-path": "~/kb",
    "stages": {"qa": {"model": "sonnet", "thinking": "medium", "repo-access": "ro"}},
}


def _setup(tmp_path: Path, schema: Path, repo_raw: dict[str, object]) -> tuple[Path, Path]:
    repo = tmp_path / "my-repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    config_dir = tmp_path / "config"
    (config_dir / "repository").mkdir(parents=True)
    shutil.copy(schema, config_dir / "config.schema.json")
    (config_dir / "global.config.json").write_text(json.dumps(GLOBAL), encoding="utf-8")
    (config_dir / "repository" / "my-repo.config.json").write_text(
        json.dumps(repo_raw), encoding="utf-8"
    )
    return repo, config_dir


def test_config_check_prints_ok(
    tmp_path: Path, schema_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repo, config_dir = _setup(tmp_path, schema_path, {})

    code = main(["config", "check", "--repo", str(repo), "--config-dir", str(config_dir)])

    assert code == 0
    assert capsys.readouterr().out.strip() == "ok"


def test_config_check_prints_errors_and_exits_1(
    tmp_path: Path, schema_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repo, config_dir = _setup(tmp_path, schema_path, {"verify": [{"run": "nope"}]})

    code = main(["config", "check", "--repo", str(repo), "--config-dir", str(config_dir)])

    assert code == 1
    out = capsys.readouterr().out
    assert "my-repo.config.json: $.verify[0].run: unknown command 'nope'" in out


def test_config_render_writes_to_out(
    tmp_path: Path, schema_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repo, config_dir = _setup(tmp_path, schema_path, {"stages": {"qa": {"thinking": "high"}}})
    out = tmp_path / "out"

    code = main(
        [
            "config",
            "render",
            "--repo",
            str(repo),
            "--config-dir",
            str(config_dir),
            "--out",
            str(out),
        ]
    )

    assert code == 0
    written = json.loads((out / "my-repo.config.json").read_text(encoding="utf-8"))
    assert written["stages"]["qa"] == {**GLOBAL["stages"]["qa"], "thinking": "high"}
    assert "ok" in capsys.readouterr().out


def test_config_render_refuses_read_only_config_dir_without_out(
    tmp_path: Path, schema_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repo, config_dir = _setup(tmp_path, schema_path, {})
    config_dir.chmod(0o555)
    try:
        code = main(["config", "render", "--repo", str(repo), "--config-dir", str(config_dir)])
    finally:
        config_dir.chmod(0o755)

    assert code == 1
    assert "--out" in capsys.readouterr().err
