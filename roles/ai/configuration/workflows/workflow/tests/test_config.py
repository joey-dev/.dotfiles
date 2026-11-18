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
