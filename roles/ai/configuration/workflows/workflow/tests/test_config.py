"""Tests for claude_workflow.config."""

from __future__ import annotations

import json
from pathlib import Path

from claude_workflow.config import RepoAccess, StageName, load_config


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
