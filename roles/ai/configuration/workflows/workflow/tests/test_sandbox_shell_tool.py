"""The debug tool tools/sandbox_shell.py must keep loading the config."""

from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
from pathlib import Path
from types import ModuleType

import pytest

TOOL = Path(__file__).resolve().parents[1] / "tools" / "sandbox_shell.py"


def _tool() -> ModuleType:
    spec = importlib.util.spec_from_file_location("sandbox_shell", TOOL)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_tool_loads_config_for_the_current_repo(
    tmp_path: Path, schema_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = tmp_path / "my-repo"
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    (repo / "sub").mkdir()
    config_dir = tmp_path / "config"
    (config_dir / "repository").mkdir(parents=True)
    shutil.copy(schema_path, config_dir / "config.schema.json")
    (config_dir / "global.config.json").write_text(json.dumps({"kb-path": "/kb"}))
    (config_dir / "repository" / "my-repo.config.json").write_text(
        json.dumps({"max-fix-rounds": 7})
    )
    monkeypatch.chdir(repo / "sub")
    tool = _tool()

    args = tool.parse_args(["qa", "--config-dir", str(config_dir)])
    config = tool.load_tool_config(args)

    assert config.repo_path == repo.resolve()
    assert config.kb_path == Path("/kb")
    assert config.max_fix_rounds == 7
