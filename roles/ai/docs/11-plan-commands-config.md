# Commands + Config Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The workflow reads the new kebab-case config (global + per-repo), runs **named commands** (`sandbox`, `host`, `container`) for Verify and for `tests.txt`, and validates every value Claude gives on the host.

**Architecture:**

- **Config:** `global.config.json` holds personal settings. `repository/<repo-name>.config.json` holds repo settings and may override any global key, down to one stage field. Both are checked against `config.schema.json` plus cross-reference checks, at startup and with `claude-workflow check-config`.
- **Commands:** one module turns a command definition plus parameter values into an argv. One runner per `run-in`.
- **`tests.txt`:** becomes `<command-name> [name=value ...]`. The `flake:` / `docker:` prefixes are dropped.

**Tech Stack:** Python 3.12, `jsonschema` (Nix: `python3Packages.jsonschema`), pytest, bubblewrap, Docker.

**Spec:** this file's "Decisions" section, plus `09-tests-and-docker.md` for the Docker rules that stay. The config files in `roles/ai/configuration/workflows/config/` are the target format.

All code paths are relative to `roles/ai/configuration/workflows/workflow/`.

---

## Decisions (from the user, 2026-11-19)

1. **kebab-case keys.** Durations are strings with a unit: `"90s"`, `"15m"`, `"2h"`.
2. **Split config:**
   - **global:** `kb-path`, `flake-path`, the limits (`max-*`, `headless-timeout`, `commit-no-verify`) and `stages`;
   - **per repo** (`repository/<repo-name>.config.json`): `commands`, `verify`, `docker-compose`, `shared-dependencies`, plus **any override** of a global key. Stages merge **per field**, so `"stages": {"qa": {"thinking": "high"}}` only changes that one field.
   - `<repo-name>` = the folder name of the repo root.
3. **`required`** (default `false`) is the only required-flag key.
4. **Parameters:** `{{name}}` in `command`; `format` with `{{value}}`; `default`; `pattern` (always a full match); `example`; `description`.
5. **`run-in`:** `sandbox` | `host` | `container`.
   - `container` = `docker exec` into a running container. It does **not** need docker compose.
   - **"Compose stack"** = the Docker Compose project in the `docker-compose` key. `needs-compose-stack: true` runs `docker compose up` for the worktree first.
6. **`timeout`** per command. Slow suites get `required: true` on their filter, so Claude can never start a full run.
7. **`tests.txt`** lists command names with parameters. Only parameters that have a `pattern` can be set there.
8. **`phpstan:changed`** is a separate command (changed PHP files, tests excluded). It is **not** in `verify`.
9. **`cs-check` (`bin/cs verify`):** the user preferred option (b), running it on the host. **The controller recommends a sandbox variant instead** (see Task 3, `needs-git`). **The user must pick before Task 3.**

### Why not option (b), running `bin/cs` on the host

The hooks in `.pre-commit-config.yaml` execute **worktree code**:

- `bin/console deptrac:analyze` boots the Symfony app, which means all PHP code Claude wrote;
- `tools/.php-cs-fixer.php` and `legacy/rector/rector.php` are PHP configs that get executed;
- `frontend/eslint.config.ts` is a TS config that gets executed;
- `vue-tsc` loads the TS project.

On the host, that is **code execution as the user** (SSH keys, `~/.claude`, `.env`). A path guard can't cover "the whole app". Also, on the host the worktree's `vendor/` and `node_modules/` are empty; the shared dependencies are only bwrap mounts.

**The sandbox variant was tested** (2026-11-19, pre-commit 4.5.1): `pre-commit run --files ...` works in a **fresh `git init` repo** with untracked files. All hooks are `repo: local`, `language: system`, so it needs **no network**. The sandbox then mounts a throwaway git dir instead of hiding `.git`.

---

## Global Constraints

- **Scope:** only `roles/ai`. The user allows `git add` / commit again; never push.
- **Security rules (keep all of them):**
  - Claude never gets Docker access.
  - Configs, schema and validation code are **never mounted into a sandbox** and **never read from the target repo or worktree**.
  - Every value from `tests.txt` is validated on the host before use: **full-match `pattern`**, `required`, a known command and known parameters.
  - A parameter without a `pattern` can't be set from `tests.txt`.
  - Values are inserted **shell-quoted, word by word**: a value with spaces becomes several arguments, never shell syntax.
  - A `host` command's script (the first word, when it's a repo path) is **protected automatically** like the compose files, and the **base-commit copy** is run.
  - `flake:`-style untrusted commands (everything from `tests.txt`) get no persistent cache. Commands from `verify` keep the Verify cache.
- **Unit tests:** `nix shell nixpkgs#python312 nixpkgs#python312Packages.pytest nixpkgs#python312Packages.jsonschema -c env PYTHONPATH=. pytest -q`. All existing tests keep passing, or are rewritten for the new format.
- **Nix build:** `nix build '.#homeConfigurations."joey@work".activationPackage' --no-link` from the dotfiles root.

## Review Focus

1. **A `tests.txt` value with shell characters** (`;`, `$( )`, backticks, newline) for a `host` command → refused, nothing runs.
2. **A pattern without `^…$`** (e.g. `[a-z]+`) must still refuse `abc;rm` → full match.
3. **Repo override of one stage field** keeps the other global fields of that stage.
4. **`changed-files` with no match and `if-none: skip`** → the command is skipped and reported as skipped, not as passed.
5. **Unknown parameter in `verify` or `tests.txt`** (typo, wrong case) → a clear error naming the command and the parameter.

---

## File Structure

| File | Responsibility |
|---|---|
| Modify `claude_workflow/config.py` | Load global + repo, merge, kebab-case, durations, schema + cross checks |
| Create `claude_workflow/commands.py` | Command and parameter models, rendering to argv, `changed-files` |
| Create `claude_workflow/runners.py` | `sandbox` / `host` / `container` runners (uses `docker_stack.py`, `sandbox.py`) |
| Modify `claude_workflow/tests_file.py` | New line format → `(command, values)` |
| Modify `claude_workflow/stages/verify.py` | Run `verify` entries, then `tests.txt`, through the runners |
| Modify `claude_workflow/stages/plan.py`, `implement.py`, `review.py`, `skills/*` | Show the command catalogue; new `tests.txt` format |
| Modify `claude_workflow/cli.py` | `check-config` subcommand; repo-name lookup |
| Modify `roles/ai/ai.nix` | `jsonschema` dependency |
| Modify `roles/ai/configuration/workflows/config/*` | Final files: trimmed repo file, schema additions |

---

### Task 1: Config loading (global + repo, kebab-case, schema)

**Interfaces:**
- `load_config(repo_root: Path, config_dir: Path | None = None) -> WorkflowConfig`. `config_dir` defaults to `$XDG_CONFIG_HOME/claude-workflow`. It reads `global.config.json`, then `repository/<repo_root.name>.config.json` when present.
- `merge_config(global_raw: dict, repo_raw: dict) -> dict`: deep merge. Objects merge key by key; arrays and scalars from the repo replace the global ones.
- `parse_duration(text: str) -> int` (seconds); raises `ValueError` for anything other than `^[1-9][0-9]*(s|m|h)$`.
- `validate_raw(raw: dict, schema_path: Path) -> list[str]`: schema errors as `"$.path: message"`, plus cross checks:
  - each `verify[].run` exists in `commands`;
  - each parameter name used exists on that command;
  - each `{{x}}` in a command has a parameter `x`;
  - `container` is set exactly when `run-in` is `container`.
- `WorkflowConfig` gains `commands: dict[str, Command]` and `verify: tuple[VerifyEntry, ...]` (models from Task 2), and drops `verify_commands`.
- CLI: `claude-workflow check-config [--repo PATH]` prints the errors (or `ok`) and exits 1 on errors. `--config` is replaced by `--config-dir`.

**Steps:**
- [ ] Tests first:
  - `test_repo_overrides_one_stage_field` (qa `thinking` high, the other qa fields from global);
  - `test_missing_repo_file_uses_global_only`;
  - `test_parse_duration` (`"90s"`→90, `"15m"`→900, `"2h"`→7200, and `"15"` / `"0m"` / `"1d"` raise);
  - `test_unknown_verify_parameter_is_reported` (`Paths` vs `paths`);
  - `test_unknown_command_in_verify_is_reported`;
  - `test_placeholder_without_parameter_is_reported`;
  - `test_real_config_dir_validates`: loads `../config/` for `dyflexis-monorepo`, skipped when absent in the Nix build.
- [ ] Implement. Keep the old snake_case loader out: there is one user and one config.
- [ ] `ai.nix`: add `python3Packages.jsonschema` to `dependencies`, and copy `config.schema.json` next to the package as a fallback. The `xdg.configFile` line is already fixed.
- [ ] Commit.

### Task 2: Command model and rendering

**Interfaces** (`commands.py`):
- `Parameter(description, required, default: str | ChangedFiles | None, format: str | None, pattern: str | None, example)`.
- `ChangedFiles(include: tuple[str, ...], exclude: tuple[str, ...], if_none: Literal["skip", "run-without"])`.
- `Command(name, description, run_in, command, working_directory, timeout, needs_compose_stack, needs_git, container, user, parameters)`.
- `VerifyEntry(run: str, values: dict[str, str | ChangedFiles])`.
- `class Skip(Exception)`: raised for `if-none: skip`.
- `render(cmd: Command, values: dict[str, str | ChangedFiles], changed: list[str], *, from_tests_file: bool) -> list[str]`:
  - resolves default → value;
  - `ChangedFiles` → paths relative to `working_directory`, keeping only files under it, filtered by fnmatch include/exclude;
  - checks `required` and the full-match `pattern` (only when `from_tests_file`; a missing pattern then raises);
  - splits each value into words, applies `format` (`{{value}}` = the quoted words), substitutes `{{name}}`, and drops empty placeholders;
  - returns `["sh", "-c", <command line>]`. Every inserted word is `shlex.quote`d.

**Steps:**
- [ ] Tests first:
  - `test_value_with_shell_chars_is_quoted`;
  - `test_pattern_is_full_match`;
  - `test_tests_file_value_without_pattern_is_refused`;
  - `test_required_missing_raises`;
  - `test_format_applied_only_when_value_present`;
  - `test_changed_files_relative_to_working_directory`;
  - `test_changed_files_none_skip_raises_skip`;
  - `test_default_can_be_changed_files`;
  - `test_multi_word_value_becomes_separate_args` (`"Core Common"` → two args).
- [ ] Implement. Commit.

### Task 3: Runners

**Decision needed first:** decision 9 (`cs-check` in the sandbox with `needs-git`, or on the host).

**Interfaces** (`runners.py`):
- `run(cmd: Command, argv: list[str], ctx: RunContext) -> tuple[str, str]` (status, output), dispatching on `run_in`:
  - **`sandbox`:** a fresh bwrap like Verify's today. `cache_dir` only when `ctx.trusted` (from `verify`). `needs-git: true` → the host makes a throwaway `git init` dir and mounts it at `<repo>/.git` instead of the mask.
  - **`host`:** guard (with the command's script added to the patterns), then the base-commit copy of that script, `cwd=worktree` (+ `working-directory`).
  - **`container`:** `docker exec [-u user] [-w working-directory] <container> sh -c <line>`. Here `working-directory` is a path **inside** the container.
  - **`needs-compose-stack`:** the existing `up` flow (`prepare_worktree`, `up_command`), at most once per Verify run.
- Generalize `docker_stack.guard_patterns(cfg)` to `guard_patterns(compose_cfg, host_scripts: tuple[str, ...])`.

**Steps:**
- [ ] Tests first:
  - `test_host_command_script_is_protected_and_base_copy_runs`;
  - `test_container_command_argv` (with and without `user`);
  - `test_needs_git_mounts_scratch_git_dir`;
  - `test_untrusted_sandbox_run_has_no_cache`;
  - `test_compose_up_once_for_two_commands`.
- [ ] Implement. Commit.

### Task 4: New `tests.txt`, Verify, prompts

**Interfaces:**
- `tests_file.parse_tests_file(text: str, commands: dict[str, Command]) -> tuple[list[TestLine], list[str]]`, with `TestLine(command: str, values: dict[str, str])`. A line is `<name> [key=value ...]`, split on whitespace; a value can't contain spaces. Unknown command or parameter → an error with the line number.
- Verify: run each `verify` entry (trusted), then each `tests.txt` line (untrusted), through `render` + `run`. `Skip` → a `SKIPPED (no changed files)` section. Keep the diff check, NEEDS_FIX / NEEDS_HUMAN, and full output.
- **Fix the parked issue from plan 10:** when sandbox checks failed, return NEEDS_FIX; ask the human (NEEDS_HUMAN) only when everything else passed.
- Plan, Implement and Review prompts include a **command catalogue** generated from the config: name, description, `run-in`, and parameters with their `example` and whether `tests.txt` may set them. Implement may run `sandbox` commands itself, with the rendered line shown.
- Skills: replace the `flake:` / `docker:` format text.

**Steps:**
- [ ] Tests first:
  - `test_tests_line_with_values`;
  - `test_tests_line_unknown_command`;
  - `test_tests_line_value_fails_pattern`;
  - `test_verify_runs_verify_entries_then_tests_file`;
  - `test_skip_is_reported_not_passed`;
  - `test_sandbox_failure_plus_guard_stop_needs_fix`;
  - `test_catalogue_in_plan_prompt`.
- [ ] Implement. Delete the old `docker_args` / prefix code. Commit.

### Task 5: Final config files and docs

- [ ] `repository/dyflexis-monorepo.config.json`: only `$schema`, `commands`, `verify`, `docker-compose`, `shared-dependencies` and real overrides. Remove the copied global keys and stages.
- [ ] Add `phpstan:changed` (default = changed PHP files, tests excluded). Set `cs-check` per decision 9 (`needs-git: true` in the sandbox variant, command `bin/cs verify`).
- [ ] Schema: add `needs-git`, allow `ChangedFiles` as a `default`, and document the merge rule. `example.config.json` follows the repo file.
- [ ] Docs: `04-file-responsibilities.md` (new modules), `09` (commands replace prefixes), `08` (status).
- [ ] `check-config` passes on the real files; the Nix build passes. Commit.

### Task 6: Real-repo checks (with the user)

This **replaces Task 7 of plan 10** and includes it. Ask before every Docker step.

- [ ] Run the commands from `verify` in a sandbox on the monorepo; check that they start and that the phpstan cache is reused.
- [ ] `cs-check` with real changed files: hooks run, and a style error fails.
- [ ] Compose: `up` from a worktree, `--wait`, `git status` stays clean, the `tests:api` filter works, and `HOST_UID` is found.
- [ ] Certs and secrets: apply the user's decisions (see `09`, "Known limits").
- [ ] First real ticket end to end; read `06-verify.md`.
