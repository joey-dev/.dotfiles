"""Check the standalone CLI using the real sandbox command builder."""

from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import patch

import pytest

from claude_workflow.create_sandbox import main


@pytest.mark.parametrize("args", [[], ["--network-access", "maybe"], [
    "--network-access", "false", "--startup", "bash", "--agent-claude"
]])
def test_requires_network_choice_and_only_one_startup(args: list[str]) -> None:
    with pytest.raises(SystemExit) as error:
        main(args)
    assert error.value.code == 2


@pytest.mark.parametrize(
    ("args", "startup"),
    [
        ([], ["/bin/bash"]),
        (["--startup", './tool "two words"'], ["./tool", "two words"]),
        (["--agent-claude"], ["claude", "--model", "sonnet", "--effort", "high"]),
    ],
)
@pytest.mark.parametrize("network", ["true", "false"])
def test_launch(
    args: list[str],
    startup: list[str],
    network: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = tmp_path / "project"
    workspace.mkdir()
    monkeypatch.chdir(workspace)
    monkeypatch.setenv("SHELL", "/bin/bash")
    home = tmp_path / "host-home"
    monkeypatch.setenv("HOME", str(home))
    claude_home = home / ".claude"
    claude_home.mkdir(parents=True)
    (claude_home / "CLAUDE.md").write_text("Host instructions")
    (claude_home / ".credentials.json").write_text("{}")

    with patch("claude_workflow.create_sandbox.subprocess.run") as run:
        run.return_value = CompletedProcess([], 42)
        assert main(["--network-access", network, *args]) == 42
    command = run.call_args.args[0]
    assert command[0] == "bwrap"
    assert command[command.index("--chdir") + 1] == str(home / workspace.name)
    assert str(workspace) in command
    assert str(claude_home / "CLAUDE.md") in command
    inner = command[command.index("--") + 1:]
    if network == "false":
        assert "--unshare-net" in command
        assert "/tmp/cw-proxy.sock" in command
        inner = inner[4:]  # sh -c <bridge script> cw-bridge
    else:
        assert "--unshare-net" not in command
        assert "/tmp/cw-proxy.sock" not in command
    assert inner[:len(startup)] == startup
    if args == ["--agent-claude"]:
        assert inner[inner.index("--permission-mode") + 1] == "dontAsk"
        assert "--strict-mcp-config" in inner
