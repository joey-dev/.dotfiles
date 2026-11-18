"""Tests for claude_workflow.config."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from claude_workflow.config import RepoAccess, StageName, WorkflowConfig, load_config
from claude_workflow.deps import SharedDependency


def test_load_config_defaults_and_json_override(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    kb = tmp_path / "kb"
    cfg_file = tmp_path / "config.json"
    cfg_file.write_text(
        json.dumps(
            {
                "repo_path": str(repo),
                "kb_path": str(kb),
                "stages": {
                    "explore": {
                        "model": "sonnet",
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    cfg = load_config(cfg_file)

    assert cfg.repo_path == repo
    assert cfg.kb_path == kb
    assert cfg.stages[StageName.EXPLORE].model == "sonnet"
    assert cfg.stages[StageName.EXPLORE].repo_access is RepoAccess.RO
    assert cfg.stages[StageName.IMPLEMENT].repo_access is RepoAccess.RW
    assert cfg.stages[StageName.INTAKE].repo_access is RepoAccess.NONE
    assert cfg.max_plan_reviews == 2


def _load(tmp_path: Path, raw: dict[str, object]) -> WorkflowConfig:
    cfg_file = tmp_path / "config.json"
    cfg_file.write_text(json.dumps(raw), encoding="utf-8")
    return load_config(cfg_file)


def test_shared_dependencies_default_is_empty(tmp_path: Path) -> None:
    assert _load(tmp_path, {}).shared_dependencies == ()


def test_shared_dependencies_are_loaded(tmp_path: Path) -> None:
    cfg = _load(
        tmp_path, {"shared_dependencies": [{"dir": "vendor", "lockfile": "composer.lock"}]}
    )

    assert cfg.shared_dependencies == (SharedDependency("vendor", "composer.lock"),)


def test_shared_dependencies_need_dir_and_lockfile(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="shared_dependencies"):
        _load(tmp_path, {"shared_dependencies": [{"dir": "vendor"}]})


def test_timeouts_have_defaults_and_must_be_positive(tmp_path: Path) -> None:
    cfg = _load(tmp_path, {})
    assert (cfg.headless_timeout, cfg.verify_timeout) == (3600, 1800)

    with pytest.raises(ValueError, match="verify_timeout"):
        _load(tmp_path, {"verify_timeout": 0})


def test_commit_no_verify_defaults_to_true(tmp_path: Path) -> None:
    assert _load(tmp_path, {}).commit_no_verify is True
    assert _load(tmp_path, {"commit_no_verify": False}).commit_no_verify is False


def _load_raw(tmp_path: Path, raw: dict[str, object]) -> WorkflowConfig:
    cfg_file = tmp_path / "config.json"
    cfg_file.write_text(json.dumps(raw), encoding="utf-8")
    return load_config(cfg_file)


def test_docker_config_defaults_to_none(tmp_path: Path) -> None:
    assert _load_raw(tmp_path, {}).docker is None
    assert _load_raw(tmp_path, {"docker": None}).docker is None


def test_docker_config_loads_project_name(tmp_path: Path) -> None:
    docker = _load_raw(tmp_path, {"docker": {"project_name": "dfs"}}).docker
    assert docker is not None
    assert docker.project_name == "dfs"
    assert docker.profile == "dyflexis"
    assert docker.up_timeout == 900


def test_docker_config_requires_project_name(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="project_name"):
        _load_raw(tmp_path, {"docker": {}})


def test_docker_config_rejects_bad_fields(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="up_timeout"):
        _load_raw(tmp_path, {"docker": {"project_name": "x", "up_timeout": 0}})
    with pytest.raises(ValueError, match="protected_paths"):
        _load_raw(tmp_path, {"docker": {"project_name": "x", "protected_paths": [""]}})


def test_real_config_json_loads_with_monorepo_settings() -> None:
    real = Path(__file__).resolve().parents[2] / "config.json"
    if not real.is_file():
        # The Nix build only sees the workflow/ directory, not its parent.
        pytest.skip("config.json is outside the package source (Nix build)")

    cfg = load_config(real)

    assert cfg.flake_path is not None
    assert str(cfg.flake_path).endswith("templates/latest")
    assert len(cfg.verify_commands) == 1
    assert "phpstan" in cfg.verify_commands[0]
    assert "$CW_CHANGED_FILES" in cfg.verify_commands[0]
    assert [d.dir for d in cfg.shared_dependencies] == [
        "legacy/vendor",
        "legacy/app/node_modules",
        "frontend/node_modules",
        "tools/vendor",
    ]
    assert cfg.docker is not None
    assert cfg.docker.project_name == "dyflexis-monorepo"
    assert cfg.docker.profile == "dyflexis"
    assert cfg.docker.host_copies == ("nginx-proxy/certs",)
    assert cfg.docker.create_dirs == ("legacy/cache",)
