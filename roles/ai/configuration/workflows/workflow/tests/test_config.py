"""Tests for claude_workflow.config (global + per-repo kebab-case config)."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import pytest

from claude_workflow.commands import ChangedFiles, VerifyEntry
from claude_workflow.config import (
    DEFAULT_PROTECTED_PATHS,
    RepoAccess,
    StageName,
    check_config,
    load_config,
    merge_config,
    parse_duration,
    render_full_config,
    validate_raw,
)

REAL_CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"


GLOBAL: dict[str, Any] = {
    "kb-path": "~/kb",
    "flake-path": None,
    "max-plan-reviews": 2,
    "max-escalations": 3,
    "max-fix-rounds": 3,
    "headless-timeout": "60m",
    "commit-no-verify": True,
    "stages": {
        "qa": {
            "model": "sonnet",
            "thinking": "medium",
            "repo-access": "ro",
            "allow-network": False,
            "mcp-config": None,
            "allowed-tools": ["Read", "Write"],
        }
    },
}

PHPSTAN: dict[str, Any] = {
    "run-in": "sandbox",
    "working-directory": "legacy",
    "command": "vendor/bin/phpstan analyze {{paths}}",
    "timeout": "15m",
    "parameters": {"paths": {"description": "Paths."}},
}


def _config_dir(
    tmp_path: Path,
    schema: Path,
    global_raw: dict[str, Any],
    repo_raw: dict[str, Any] | None,
) -> Path:
    config_dir = tmp_path / "config"
    (config_dir / "repository").mkdir(parents=True)
    shutil.copy(schema, config_dir / "config.schema.json")
    (config_dir / "global.config.json").write_text(json.dumps(global_raw), encoding="utf-8")
    if repo_raw is not None:
        (config_dir / "repository" / "my-repo.config.json").write_text(
            json.dumps(repo_raw), encoding="utf-8"
        )
    return config_dir


def _repo(tmp_path: Path) -> Path:
    repo = tmp_path / "my-repo"
    repo.mkdir()
    return repo


def test_parse_duration() -> None:
    assert parse_duration("90s") == 90
    assert parse_duration("15m") == 900
    assert parse_duration("2h") == 7200
    for bad in ("15", "0m", "1d", "", "m", " 5m", "5m "):
        with pytest.raises(ValueError):
            parse_duration(bad)


def test_merge_config_merges_objects_and_replaces_lists() -> None:
    merged = merge_config(
        {"a": {"x": 1, "y": [1, 2]}, "b": 1},
        {"a": {"y": [3]}, "c": 2},
    )
    assert merged == {"a": {"x": 1, "y": [3]}, "b": 1, "c": 2}


def test_repo_overrides_one_stage_field(tmp_path: Path, schema_path: Path) -> None:
    config_dir = _config_dir(
        tmp_path, schema_path, GLOBAL, {"stages": {"qa": {"thinking": "high"}}}
    )

    cfg = load_config(_repo(tmp_path), config_dir)

    qa = cfg.stages[StageName.QA]
    assert qa.thinking == "high"
    assert qa.model == "sonnet"
    assert qa.repo_access is RepoAccess.RO
    assert qa.allow_network is False
    assert qa.allowed_tools == ("Read", "Write")


def test_missing_repo_file_uses_global_only(tmp_path: Path, schema_path: Path) -> None:
    config_dir = _config_dir(tmp_path, schema_path, GLOBAL, None)
    repo = _repo(tmp_path)

    cfg = load_config(repo, config_dir)

    assert cfg.repo_path == repo
    assert cfg.kb_path == Path.home() / "kb"
    assert cfg.flake_path is None
    assert cfg.headless_timeout == 3600
    assert cfg.commands == {}
    assert cfg.verify == ()
    assert cfg.docker is None
    assert cfg.shared_dependencies == ()
    # Stages missing from the config keep the built-in defaults.
    assert cfg.stages[StageName.IMPLEMENT].repo_access is RepoAccess.RW


def test_repo_keys_are_loaded(tmp_path: Path, schema_path: Path) -> None:
    repo_raw = {
        "commands": {"phpstan": PHPSTAN},
        "verify": [
            {"run": "phpstan", "parameters": {"paths": "Core Common"}},
            {
                "run": "phpstan",
                "parameters": {"paths": {"changed-files": {"include": ["*.php"]}}},
            },
        ],
        "shared-dependencies": [{"dir": "vendor", "lockfile": "composer.lock"}],
        "docker-compose": {
            "project-name": "dfs",
            "up-timeout": "20m",
            "protected-paths": ["bin/*"],
            "host-copies": ["nginx-proxy/certs"],
        },
    }
    cfg = load_config(_repo(tmp_path), _config_dir(tmp_path, schema_path, GLOBAL, repo_raw))

    phpstan = cfg.commands["phpstan"]
    assert (phpstan.run_in, phpstan.timeout, phpstan.working_directory) == (
        "sandbox",
        900,
        "legacy",
    )
    assert phpstan.parameters["paths"].description == "Paths."
    assert cfg.verify == (
        VerifyEntry(run="phpstan", values={"paths": "Core Common"}),
        VerifyEntry(
            run="phpstan",
            values={"paths": ChangedFiles(include=("*.php",), exclude=(), if_none="skip")},
        ),
    )
    assert [d.dir for d in cfg.shared_dependencies] == ["vendor"]
    assert cfg.docker is not None
    assert cfg.docker.project_name == "dfs"
    assert cfg.docker.profile == "dyflexis"
    assert cfg.docker.up_timeout == 1200
    assert cfg.docker.protected_paths == (*DEFAULT_PROTECTED_PATHS, "bin/*")
    assert cfg.docker.host_copies == ("nginx-proxy/certs",)


def test_load_config_raises_with_source_file_on_errors(tmp_path: Path, schema_path: Path) -> None:
    config_dir = _config_dir(tmp_path, schema_path, GLOBAL, {"verify": [{"run": "nope"}]})

    with pytest.raises(ValueError) as excinfo:
        load_config(_repo(tmp_path), config_dir)

    message = str(excinfo.value)
    assert "my-repo.config.json" in message
    assert "$.verify[0].run" in message
    assert "nope" in message


def test_missing_global_file_is_an_error(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="global.config.json"):
        load_config(_repo(tmp_path), tmp_path / "empty")


def test_schema_error_is_reported_with_path(schema_path: Path) -> None:
    errors = validate_raw({"max-escalations": -1, "headless-timeout": "5"}, schema_path)

    assert any(e.startswith("$.max-escalations:") for e in errors)
    assert any(e.startswith("$.headless-timeout:") for e in errors)


def test_unknown_verify_parameter_is_reported(schema_path: Path) -> None:
    raw = {
        "commands": {"phpstan": PHPSTAN},
        "verify": [{"run": "phpstan", "parameters": {"Paths": "src"}}],
    }

    errors = validate_raw(raw, schema_path)

    # The schema also flags 'Paths' as not kebab-case; the cross check names the command.
    assert "$.verify[0].parameters.Paths: command 'phpstan' has no parameter 'Paths'" in errors


def test_unknown_command_in_verify_is_reported(schema_path: Path) -> None:
    raw = {"commands": {"phpstan": PHPSTAN}, "verify": [{"run": "phpunit"}]}

    errors = validate_raw(raw, schema_path)

    assert errors == ["$.verify[0].run: unknown command 'phpunit'"]


def test_placeholder_without_parameter_is_reported(schema_path: Path) -> None:
    raw = {"commands": {"phpunit": {"run-in": "sandbox", "command": "phpunit {{filter}}"}}}

    errors = validate_raw(raw, schema_path)

    assert errors == [
        "$.commands.phpunit.command: placeholder '{{filter}}' has no parameter 'filter'"
    ]


def test_container_must_match_run_in(schema_path: Path) -> None:
    raw = {
        "commands": {
            "a": {"run-in": "container", "command": "true"},
            "b": {"run-in": "sandbox", "command": "true", "container": "web"},
        }
    }

    errors = validate_raw(raw, schema_path)

    assert errors == [
        "$.commands.a: run-in 'container' needs 'container'",
        "$.commands.b.container: only allowed with run-in 'container'",
    ]


def test_check_config_names_the_global_file(tmp_path: Path, schema_path: Path) -> None:
    config_dir = _config_dir(tmp_path, schema_path, {**GLOBAL, "max-fix-rounds": -1}, {})

    errors = check_config(_repo(tmp_path), config_dir)

    assert len(errors) == 1
    assert errors[0].startswith(f"{config_dir / 'global.config.json'}: $.max-fix-rounds:")


def test_render_writes_merged_config_and_returns_errors(tmp_path: Path, schema_path: Path) -> None:
    config_dir = _config_dir(
        tmp_path,
        schema_path,
        GLOBAL,
        {"stages": {"qa": {"thinking": "high"}}, "verify": [{"run": "x"}]},
    )
    out_dir = tmp_path / "out"

    path, errors = render_full_config(_repo(tmp_path), config_dir, out_dir)

    assert path == out_dir / "my-repo.config.json"
    written = json.loads(path.read_text(encoding="utf-8"))
    assert written["stages"]["qa"]["thinking"] == "high"
    assert written["stages"]["qa"]["model"] == "sonnet"
    assert written["kb-path"] == "~/kb"
    assert written["$schema"] == str((config_dir / "config.schema.json").resolve())
    assert len(errors) == 1
    assert "my-repo.config.json: $.verify[0].run: unknown command 'x'" in errors[0]


def test_real_config_dir_validates(tmp_path: Path) -> None:
    if not (REAL_CONFIG_DIR / "global.config.json").is_file():
        # The Nix build only sees the workflow/ directory, not its parent.
        pytest.skip("config/ is outside the package source (Nix build)")
    repo = tmp_path / "dyflexis-monorepo"
    repo.mkdir()

    assert check_config(repo, REAL_CONFIG_DIR) == []
    cfg = load_config(repo, REAL_CONFIG_DIR)

    assert cfg.flake_path is not None
    assert str(cfg.flake_path).endswith("templates/latest")
    assert "phpstan" in cfg.commands
    assert all(entry.run in cfg.commands for entry in cfg.verify)
    assert [d.dir for d in cfg.shared_dependencies] == [
        "legacy/vendor",
        "legacy/app/node_modules",
        "frontend/node_modules",
        "tools/vendor",
    ]
    assert cfg.docker is not None
    assert cfg.docker.project_name == "dyflexis-monorepo"
    assert cfg.docker.host_copies == ("nginx-proxy/certs",)
    assert cfg.docker.create_dirs == ("legacy/cache",)


def test_example_config_validates(schema_path: Path) -> None:
    example = REAL_CONFIG_DIR / "example.config.json"
    if not example.is_file():
        pytest.skip("config/ is outside the package source (Nix build)")
    raw = json.loads(example.read_text(encoding="utf-8"))

    assert validate_raw(raw, schema_path) == []


def test_schema_accepts_needs_git_and_changed_files_default(schema_path: Path) -> None:
    raw = {
        "commands": {
            "stan": {
                "run-in": "sandbox",
                "command": "stan {{paths}}",
                "needs-git": True,
                "parameters": {"paths": {"default": {"changed-files": {"include": ["*.php"]}}}},
            }
        }
    }

    assert validate_raw(raw, schema_path) == []


def test_typo_key_in_repo_file_names_the_repo_file(tmp_path: Path, schema_path: Path) -> None:
    config_dir = _config_dir(tmp_path, schema_path, GLOBAL, {"comands": {}})

    errors = check_config(_repo(tmp_path), config_dir)

    repo_file = config_dir / "repository" / "my-repo.config.json"
    assert errors == [
        f"{repo_file}: $: Additional properties are not allowed ('comands' was unexpected)"
    ]


def test_typo_key_in_global_file_names_the_global_file(tmp_path: Path, schema_path: Path) -> None:
    config_dir = _config_dir(tmp_path, schema_path, {**GLOBAL, "kb-pth": "x"}, {"comands": {}})

    errors = check_config(_repo(tmp_path), config_dir)

    assert sorted(errors) == sorted(
        [
            f"{config_dir / 'global.config.json'}: $: Additional properties are not allowed "
            "('kb-pth' was unexpected)",
            f"{config_dir / 'repository' / 'my-repo.config.json'}: $: Additional properties are "
            "not allowed ('comands' was unexpected)",
        ]
    )


def test_bad_name_in_repo_commands_names_the_repo_file(tmp_path: Path, schema_path: Path) -> None:
    repo_raw = {"commands": {"Bad_Name": {"run-in": "sandbox", "command": "true"}}}
    config_dir = _config_dir(tmp_path, schema_path, GLOBAL, repo_raw)

    errors = check_config(_repo(tmp_path), config_dir)

    assert len(errors) == 1
    assert errors[0].startswith(f"{config_dir / 'repository' / 'my-repo.config.json'}: $.commands:")


def test_placeholder_inside_quotes_is_reported(schema_path: Path) -> None:
    raw = {
        "commands": {
            "a": {
                "run-in": "sandbox",
                "command": 'run "{{x}}"',
                "parameters": {"x": {"format": "--f='{{value}}'"}},
            }
        }
    }

    errors = validate_raw(raw, schema_path)

    assert errors == [
        "$.commands.a.command: placeholder '{{x}}' sits inside quotes",
        "$.commands.a.parameters.x.format: '{{value}}' sits inside quotes",
    ]


def test_host_command_must_start_with_a_repo_script(schema_path: Path) -> None:
    raw = {
        "commands": {
            "make": {"run-in": "host", "command": "make test"},
            "npm": {"run-in": "host", "command": "npm run x"},
            "abs": {"run-in": "host", "command": "/usr/bin/x"},
            "up": {"run-in": "host", "command": "../x.sh"},
            "ok1": {"run-in": "host", "command": "./test_runner.sh api"},
            "ok2": {"run-in": "host", "command": "bin/cs"},
        }
    }

    errors = validate_raw(raw, schema_path)

    assert len(errors) == 4
    for name in ("make", "npm", "abs", "up"):
        (error,) = [e for e in errors if e.startswith(f"$.commands.{name}.command:")]
        assert "repo script" in error or "leaves the repository" in error


def test_needs_git_only_with_run_in_sandbox(schema_path: Path) -> None:
    raw = {
        "commands": {
            "h": {"run-in": "host", "command": "bin/cs", "needs-git": True},
            "c": {"run-in": "container", "container": "web", "command": "x", "needs-git": True},
            "s": {"run-in": "sandbox", "command": "bin/cs", "needs-git": True},
            "f": {"run-in": "host", "command": "bin/cs", "needs-git": False},
        }
    }

    errors = validate_raw(raw, schema_path)

    assert errors == [
        "$.commands.h.needs-git: only allowed with run-in 'sandbox'",
        "$.commands.c.needs-git: only allowed with run-in 'sandbox'",
    ]


def test_docker_host_copy_include_and_services(tmp_path: Path, schema_path: Path) -> None:
    repo_raw = {
        "docker-compose": {
            "project-name": "dfs",
            "host-copies": [
                "plain/dir",
                {"path": "nginx-proxy/certs", "include": ["*.crt"]},
            ],
            "services": ["db", "redis"],
        },
    }
    cfg = load_config(_repo(tmp_path), _config_dir(tmp_path, schema_path, GLOBAL, repo_raw))

    assert cfg.docker is not None
    assert cfg.docker.host_copies == ("plain/dir", "nginx-proxy/certs")
    assert cfg.docker.host_copy_includes == (("nginx-proxy/certs", ("*.crt",)),)
    assert cfg.docker.services == ("db", "redis")


def _real_commands(tmp_path: Path) -> dict[str, Any]:
    if not (REAL_CONFIG_DIR / "global.config.json").is_file():
        pytest.skip("config/ is outside the package source (Nix build)")
    repo = tmp_path / "dyflexis-monorepo"
    repo.mkdir()
    return dict(load_config(repo, REAL_CONFIG_DIR).commands)


def test_real_cs_check_renders_changed_files(tmp_path: Path) -> None:
    from claude_workflow.commands import Skip, render

    cs = _real_commands(tmp_path)["cs-check"]
    with pytest.raises(Skip):
        render(cs, {}, [], from_tests_file=False)
    assert render(cs, {}, ["a.php", "front end/b.ts"], from_tests_file=False) == [
        "sh",
        "-c",
        "bin/cs a.php 'front end/b.ts'",
    ]


def test_example_cs_check_renders_changed_files(schema_path: Path) -> None:
    from claude_workflow.commands import parse_commands, render

    example = REAL_CONFIG_DIR / "example.config.json"
    if not example.is_file():
        pytest.skip("config/ is outside the package source (Nix build)")
    cs = parse_commands(json.loads(example.read_text(encoding="utf-8"))["commands"])["cs-check"]
    assert render(cs, {}, ["a.php"], from_tests_file=False) == ["sh", "-c", "bin/cs a.php"]


def test_real_phpstan_changed_excludes_codeception_tests(tmp_path: Path) -> None:
    from claude_workflow.commands import Skip, render

    stan = _real_commands(tmp_path)["phpstan:changed"]
    changed = ["legacy/src/Foo.php", "legacy/tests/api/InvoiceCest.php", "legacy/src/FooTest.php"]
    argv = render(stan, {}, changed, from_tests_file=False)
    assert "src/Foo.php" in argv[2]
    assert "Cest" not in argv[2] and "FooTest" not in argv[2]
    with pytest.raises(Skip):
        render(stan, {}, ["legacy/tests/unit/X.php"], from_tests_file=False)
