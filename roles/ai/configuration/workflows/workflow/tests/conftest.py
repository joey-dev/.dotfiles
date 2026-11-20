"""Shared pytest fixtures."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

REAL_CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"


@pytest.fixture
def schema_path() -> Path:
    """The real config schema: next to the source tree, or from the Nix build (preCheck)."""
    local = REAL_CONFIG_DIR / "config.schema.json"
    if local.is_file():
        return local
    env = os.environ.get("CLAUDE_WORKFLOW_SCHEMA")
    if env and Path(env).is_file():
        return Path(env)
    pytest.skip("config.schema.json not available")


@pytest.fixture(autouse=True)
def _isolated_state_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Default state_base must never point at the real ~/.local/state."""
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "xdg-state"))
