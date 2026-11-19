"""Tests for render() in claude_workflow.commands."""

from __future__ import annotations

import pytest

from claude_workflow.commands import ChangedFiles, Command, Parameter, Skip, render


def make(command: str, params: dict[str, Parameter], wd: str | None = None) -> Command:
    return Command(
        name="cmd",
        description="",
        run_in="sandbox",
        command=command,
        working_directory=wd,
        timeout=60,
        needs_compose_stack=False,
        needs_git=False,
        container=None,
        user=None,
        parameters=params,
    )


def line(argv: list[str]) -> str:
    assert argv[:2] == ["sh", "-c"] and len(argv) == 3
    return argv[2]


def test_value_with_shell_chars_is_quoted() -> None:
    cmd = make("run {{x}}", {"x": Parameter(pattern=".*")})

    out = line(render(cmd, {"x": "a;rm /$(id)"}, [], from_tests_file=True))

    assert out == "run 'a;rm' '/$(id)'"


def test_pattern_is_full_match() -> None:
    cmd = make("run {{x}}", {"x": Parameter(pattern="[a-z]+")})

    with pytest.raises(ValueError, match="cmd.*x"):
        render(cmd, {"x": "abc; ls"}, [], from_tests_file=True)
    with pytest.raises(ValueError):
        render(cmd, {"x": "1abc"}, [], from_tests_file=True)
    assert line(render(cmd, {"x": "abc"}, [], from_tests_file=True)) == "run abc"


def test_tests_file_value_without_pattern_is_refused() -> None:
    cmd = make("run {{x}}", {"x": Parameter()})

    with pytest.raises(ValueError, match="cmd.*x.*pattern"):
        render(cmd, {"x": "abc"}, [], from_tests_file=True)
    assert line(render(cmd, {"x": "abc"}, [], from_tests_file=False)) == "run abc"


def test_tests_file_value_with_newline_or_nul_is_refused() -> None:
    cmd = make("run {{x}}", {"x": Parameter(pattern=".*", )})

    for bad in ("a\nb", "a\x00b"):
        with pytest.raises(ValueError):
            render(cmd, {"x": bad}, [], from_tests_file=True)


def test_unknown_parameter_raises() -> None:
    cmd = make("run", {})

    with pytest.raises(ValueError, match="cmd.*nope"):
        render(cmd, {"nope": "1"}, [], from_tests_file=False)


def test_required_missing_raises() -> None:
    cmd = make("run {{x}}", {"x": Parameter(required=True)})

    with pytest.raises(ValueError, match="cmd.*x.*required"):
        render(cmd, {}, [], from_tests_file=False)


def test_format_applied_only_when_value_present() -> None:
    cmd = make("run {{x}} end", {"x": Parameter(format="--filter {{value}}")})

    assert line(render(cmd, {"x": "Foo"}, [], from_tests_file=False)) == "run --filter Foo end"
    assert line(render(cmd, {}, [], from_tests_file=False)) == "run end"


def test_default_is_used_when_no_value() -> None:
    cmd = make("run {{x}}", {"x": Parameter(default="-v")})

    assert line(render(cmd, {}, [], from_tests_file=True)) == "run -v"


def test_changed_files_relative_to_working_directory() -> None:
    cmd = make("lint {{files}}", {"files": Parameter()}, wd="app")
    cf = ChangedFiles(include=("*.php",), exclude=("*Test.php",))
    changed = ["app/src/A.php", "app/src/ATest.php", "web/B.php", "app/c.js"]

    out = line(render(cmd, {"files": cf}, changed, from_tests_file=False))

    assert out == "lint src/A.php"


def test_changed_files_without_working_directory_keeps_all() -> None:
    cmd = make("lint {{files}}", {"files": Parameter()})
    cf = ChangedFiles(include=("*.php",))

    out = line(render(cmd, {"files": cf}, ["a b.php", "d/e.php"], from_tests_file=False))

    assert out == "lint 'a b.php' d/e.php"


def test_changed_files_none_skip_raises_skip() -> None:
    cmd = make("lint {{files}}", {"files": Parameter()}, wd="app")

    with pytest.raises(Skip):
        render(cmd, {"files": ChangedFiles(if_none="skip")}, ["web/x.php"], from_tests_file=False)


def test_changed_files_none_run_without_drops_placeholder() -> None:
    cmd = make("lint {{files}}", {"files": Parameter(format="-- {{value}}")})
    cf = ChangedFiles(if_none="run-without")

    assert line(render(cmd, {"files": cf}, [], from_tests_file=False)) == "lint"


def test_default_can_be_changed_files() -> None:
    cf = ChangedFiles(include=("*.php",))
    cmd = make("lint {{files}}", {"files": Parameter(default=cf)})

    out = line(render(cmd, {}, ["x.php", "y.js"], from_tests_file=True))

    assert out == "lint x.php"


def test_multi_word_value_becomes_separate_args() -> None:
    cmd = make("run {{x}}", {"x": Parameter(pattern="[A-Za-z ]+")})

    out = line(render(cmd, {"x": "Core Common"}, [], from_tests_file=True))

    assert out == "run Core Common"


def test_changed_files_from_tests_file_is_refused() -> None:
    cmd = make("lint {{files}}", {"files": Parameter(pattern=".*")})

    with pytest.raises(ValueError, match="cmd.*files"):
        render(cmd, {"files": ChangedFiles()}, ["a"], from_tests_file=True)


def test_double_space_filename_stays_intact() -> None:
    cmd = make("lint {{files}}", {"files": Parameter()})

    out = line(render(cmd, {"files": ChangedFiles()}, ["a  b.php"], from_tests_file=False))

    assert out == "lint 'a  b.php'"


def test_double_space_in_trusted_text_is_kept() -> None:
    cmd = make("printf '%s  %s' {{x}}", {"x": Parameter()})

    assert line(render(cmd, {"x": "a"}, [], from_tests_file=False)) == "printf '%s  %s' a"


@pytest.mark.parametrize("name", ["--configuration=evil.php", "-c.php"])
def test_changed_file_starting_with_dash_gets_dot_slash(name: str) -> None:
    cmd = make("phpstan {{files}}", {"files": Parameter()})

    out = line(render(cmd, {"files": ChangedFiles()}, [name], from_tests_file=False))

    assert out == f"phpstan ./{name}"


def test_dash_file_under_working_directory_gets_dot_slash() -> None:
    cmd = make("phpstan {{files}}", {"files": Parameter()}, wd="app")

    out = line(render(cmd, {"files": ChangedFiles()}, ["app/-c.php"], from_tests_file=False))

    assert out == "phpstan ./-c.php"


@pytest.mark.parametrize("text", ['run "{{x}}"', "--f='{{x}}'", "run \"a $(b) '{{x}}'\""])
def test_placeholder_inside_quotes_is_refused(text: str) -> None:
    cmd = make(text, {"x": Parameter()})

    with pytest.raises(ValueError, match="cmd.*inside quotes"):
        render(cmd, {"x": "v"}, [], from_tests_file=False)


def test_format_value_inside_quotes_is_refused() -> None:
    cmd = make("run {{x}}", {"x": Parameter(format="'{{value}}'")})

    with pytest.raises(ValueError, match="cmd.*x.*inside quotes"):
        render(cmd, {"x": "v"}, [], from_tests_file=False)


def test_placeholder_outside_quotes_next_to_quoted_text_is_ok() -> None:
    cmd = make("run 'a b' {{x}} \"c\" \\\"{{x}}", {"x": Parameter()})

    assert line(render(cmd, {"x": "v"}, [], from_tests_file=False)) == "run 'a b' v \"c\" \\\"v"


# --- tests.txt values: no leading '-', no '..' ------------------------------------------


def _filter_cmd() -> Command:
    return make("run {{filter}}", {"filter": Parameter(pattern=r"[A-Za-z0-9_./:=-]+")})


@pytest.mark.parametrize("value", ["--config=/etc/x", "-x", "ok -rf", "a --b"])
def test_tests_file_value_words_may_not_start_with_dash(value: str) -> None:
    with pytest.raises(ValueError, match="cmd.*filter.*'-'"):
        render(_filter_cmd(), {"filter": value}, [], from_tests_file=True)


@pytest.mark.parametrize("value", ["../x", "a/../b", "a/..", ".."])
def test_tests_file_value_words_may_not_contain_dotdot_segment(value: str) -> None:
    with pytest.raises(ValueError, match="cmd.*filter.*'\\.\\.'"):
        render(_filter_cmd(), {"filter": value}, [], from_tests_file=True)


def test_tests_file_dots_inside_names_are_fine() -> None:
    argv = render(_filter_cmd(), {"filter": "a..b/c.php"}, [], from_tests_file=True)
    assert line(argv) == "run a..b/c.php"


def test_config_values_may_start_with_dash() -> None:
    argv = render(_filter_cmd(), {"filter": "--x"}, [], from_tests_file=False)
    assert line(argv) == "run --x"
