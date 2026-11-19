# Tests + Docker Implementation Plan

> **Status (2026-11-19):** Tasks 1-6 done (commit `f1b50ed`). Task 7 moved into `11-plan-commands-config.md`, Task 6. See `08-next-session.md` for the current status.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement and Verify run the ticket's own tests (flake and Docker) on `dyflexis-monorepo`, plus phpstan on changed files.

**Architecture:**

- A per-ticket **`tests.txt`** (written by Plan, extended by Review) lists `flake:` and `docker:` lines.
- **Verify** runs the fixed checks and `flake:` lines in the sandbox (no network).
- Then, on the **host**, after a guard on Docker-related files, Verify starts the compose stack from the worktree and runs `docker:` lines through `test_runner.sh`.
- **Claude never touches Docker.**

**Tech Stack:** Python 3.12, pytest, bubblewrap, Docker Compose 5.4, Nix flake dev shell.

**Spec:** `roles/ai/docs/09-tests-and-docker.md` (read it first).

All paths below are relative to `roles/ai/configuration/workflows/workflow/` unless they start with `roles/`.

---

## Global Constraints

- **Scope:** only `roles/ai`. **No git commit or push**: the user commits. New files must be `git add`-ed (not committed) before a Nix build.
- **Claude never gets Docker access.** No Docker socket in any sandbox; Docker commands only run in the host-side Python.
- **Never run a worktree file on the host** unless it equals the base commit (`test_runner.sh`, compose files).
- **Never copy `.env` into the worktree.** Use the main checkout's `.env` via `--env-file` / `COMPOSE_ENV_FILES`.
- **Verify sandbox stays `--unshare-net`.** Implement stays Anthropic-only.
- **Migrations:** Claude only edits or adds files in `legacy/app/atlas-migrations/customer/schema/tables`; it never writes or runs a migration.
- **Unit tests:** `nix shell nixpkgs#python312 nixpkgs#python312Packages.pytest -c python -m pytest -q` (from the workflow dir). All 123 existing tests must keep passing.

## Review Focus

1. **A gitignored `.env` or `docker-compose.override.yml` in the worktree.** Expect the guard to refuse (Task 3 test `test_guard_flags_ignored_env_file`).
2. **A `docker:` line with shell characters** (`api ; rm -rf ~`, `` `x` ``, `$(x)`). Expect a FAIL line in `06-verify.md` and no command run (Task 1 test `test_docker_args_reject_shell_characters`).
3. **No `tests.txt`, or an empty one.** Missing → NEEDS_FIX telling Implement to write it. Empty → allowed, noted in `06-verify.md` (Task 4 tests).
4. **Review edits `tests.txt` but writes APPROVED.** Expect NEEDS_FIX so the suggested tests do run (Task 5 test `test_review_test_suggestion_forces_fix_round`).
5. **Deleted PHP files in the changed list.** phpstan must not get paths that no longer exist (Task 2 test `test_changed_paths_skips_deleted_files`).

---

## File Structure

| File | Responsibility |
|---|---|
| Create `claude_workflow/tests_file.py` | Parse and validate `tests.txt` |
| Create `claude_workflow/docker_stack.py` | Guard, compose env, `up`, run `test_runner.sh` lines (host side) |
| Modify `claude_workflow/git_host.py` | `changed_paths()`, `ignored_paths()` |
| Modify `claude_workflow/config.py` | `DockerConfig`, `WorkflowConfig.docker`, loader |
| Modify `claude_workflow/sandbox.py` | `SandboxSpec.cache_dir` → bind + `TMPDIR` |
| Modify `claude_workflow/stages/base.py` | `stage_cache_dir()`; set `cache_dir` for Implement/Verify |
| Modify `claude_workflow/stages/verify.py` | Run fixed checks + `tests.txt`; Docker step |
| Modify `claude_workflow/stages/plan.py`, `implement.py`, `review.py` | Prompts; Review's `tests.txt` rule |
| Modify `skills/plan|implement|review/SKILL.md` | `tests.txt` format, migrations rule |
| Modify `roles/ai/configuration/workflows/config.json` | Monorepo values |
| Create `tests/test_tests_file.py`, `tests/test_docker_stack.py` | New unit tests |
| Modify `tests/test_config.py`, `test_sandbox.py`, `test_git_host.py`, `test_fix_loop.py` | Extra tests |

---

### Task 1: `tests.txt` parser

**Files:**
- Create: `claude_workflow/tests_file.py`
- Test: `tests/test_tests_file.py`

**Interfaces:**
- Produces:
  - `TESTS_FILE = "tests.txt"`
  - `DOCKER_TEST_TYPES: frozenset[str] = {"unit", "integration", "api", "mobile-api", "acceptance", "codecept-build"}`
  - `@dataclass(frozen=True) class TestLine: kind: Literal["flake", "docker"]; text: str` with class attribute `__test__ = False` (so pytest does not try to collect it)
  - `parse_tests_file(text: str) -> tuple[list[TestLine], list[str]]`: (valid lines, error messages). Blank lines and `#` comments are skipped. Each error names the line number.
  - `docker_args(text: str) -> list[str]`: raises `ValueError`.

**Rules:**
- A line is `flake: <shell command>` or `docker: <args>`. Anything else is an error.
- `docker_args` splits on whitespace (no shell parsing). The first token must be in `DOCKER_TEST_TYPES`, and `debug` is not allowed. Every token must match `^[A-Za-z0-9_./:=@,+-]+$`.

- [ ] **Step 1: Write the failing tests**

```python
def test_parses_flake_and_docker_lines() -> None:
    lines, errors = parse_tests_file(
        "# comment\n\nflake: cd frontend && pnpm run test:unit a.spec.ts\ndocker: api FooCest\n"
    )
    assert errors == []
    assert lines == [
        TestLine("flake", "cd frontend && pnpm run test:unit a.spec.ts"),
        TestLine("docker", "api FooCest"),
    ]

def test_unknown_prefix_is_an_error_with_line_number() -> None:
    _, errors = parse_tests_file("flake: ok\nshell: rm -rf /\n")
    assert len(errors) == 1 and "line 2" in errors[0]

def test_docker_args_split_without_shell() -> None:
    assert docker_args("unit --group foo tests/Unit/FooTest.php") == [
        "unit", "--group", "foo", "tests/Unit/FooTest.php"]

@pytest.mark.parametrize("bad", ["api ; rm -rf ~", "api `x`", "api $(x)", "api a|b", "api 'x'"])
def test_docker_args_reject_shell_characters(bad: str) -> None:
    with pytest.raises(ValueError):
        docker_args(bad)

@pytest.mark.parametrize("bad", ["", "debug api", "shell api", "phpunit"])
def test_docker_args_reject_unknown_type(bad: str) -> None:
    with pytest.raises(ValueError):
        docker_args(bad)
```

- [ ] **Step 2: Run, expect FAIL** (`ModuleNotFoundError: claude_workflow.tests_file`)

Run: `… -m pytest -q tests/test_tests_file.py`

- [ ] **Step 3: Implement** `tests_file.py` with the interfaces above.
- [ ] **Step 4: Run, expect PASS.**
- [ ] **Step 5:** `git add claude_workflow/tests_file.py tests/test_tests_file.py` (no commit).

---

### Task 2: Changed and ignored paths

**Files:**
- Modify: `claude_workflow/git_host.py`
- Test: `tests/test_git_host.py` (reuse its temp-repo helpers)

**Interfaces:**
- Produces:
  - `changed_paths(worktree_path: Path, base_ref: str) -> list[str]`: sorted repo-relative paths. Includes tracked changes vs `base_ref` and untracked (not ignored) files. Excludes deleted files.
  - `touched_paths(worktree_path: Path, base_ref: str) -> list[str]`: same, but **including** deleted files (for the guard).
  - `ignored_paths(worktree_path: Path) -> list[str]`: `git ls-files --others --ignored --exclude-standard --directory`, with the trailing `/` stripped.

- [ ] **Step 1: Write the failing tests**
  - `test_changed_paths_lists_modified_and_untracked`: modify `a.php`, add untracked `b.php` → `["a.php", "b.php"]`.
  - `test_changed_paths_skips_deleted_files`: delete tracked `c.php` → not in `changed_paths`, but in `touched_paths`.
  - `test_ignored_paths_lists_gitignored_env`: `.gitignore` has `.env`, create `.env` → `".env" in ignored_paths(repo)`.
- [ ] **Step 2: Run, expect FAIL** (ImportError).
- [ ] **Step 3: Implement.** Use `git diff --name-only --no-renames [--diff-filter=d] base --` plus `ls-files --others --exclude-standard`. Use `-z` output.
- [ ] **Step 4: Run, expect PASS.**

---

### Task 3: Docker config, guard and stack runner

**Files:**
- Modify: `claude_workflow/config.py`
- Create: `claude_workflow/docker_stack.py`
- Test: `tests/test_config.py`, `tests/test_docker_stack.py`

**Interfaces:**
- Consumes: `touched_paths`, `ignored_paths` (Task 2), `docker_args` (Task 1).
- Produces (config):

```python
DEFAULT_PROTECTED_PATHS: tuple[str, ...] = (
    "test_runner.sh", ".env", ".env.*",
    "docker-compose.yml", "docker-compose.*.yml", "docker-compose.*.yaml",
    "compose.yml", "compose.yaml", "compose.*.yml", "compose.*.yaml",
    "legacy/docker/*", "nginx-proxy/*", "*Dockerfile", "*.Dockerfile",
)

@dataclass(frozen=True)
class DockerConfig:
    project_name: str
    profile: str = "dyflexis"
    test_runner: str = "test_runner.sh"
    up_timeout: int = 900
    protected_paths: tuple[str, ...] = DEFAULT_PROTECTED_PATHS
    # Gitignored folders the stack mounts, copied from the main checkout before `up`.
    host_copies: tuple[str, ...] = ()
    # Gitignored folders the stack mounts that only need to exist (rebuilt by the app).
    create_dirs: tuple[str, ...] = ()
```

  - **Why `host_copies`:** `nginx-proxy/certs` is gitignored, so a fresh worktree lacks it, but the proxy mounts it. It may hold a **CA private key**, so Claude must never see it: every sandbox hides these folders with a `--tmpfs` (see Task 4).

  - `WorkflowConfig.docker: DockerConfig | None = None`.
  - JSON key `"docker"`: `null` or an object. `project_name` is required and nonempty. `up_timeout` is a positive int. `protected_paths` is a list of nonempty strings. Errors raise `ValueError` naming the field.

- Produces (`docker_stack.py`):
  - `guard_violations(worktree: Path, base_ref: str, patterns: tuple[str, ...], host_copies: tuple[str, ...] = ()) -> list[str]`: sorted paths from `touched_paths` + `ignored_paths` that match a pattern (`fnmatch.fnmatch`). Paths equal to or under a `host_copies` entry are skipped (the host overwrites them anyway).
  - `prepare_worktree(cfg: DockerConfig, worktree: Path, repo: Path) -> None`: for each `host_copies` entry, delete the worktree copy and copy the main checkout's folder (`shutil.copytree`, `symlinks=True`; refuse if the source or target is a symlink). Then `mkdir(parents=True, exist_ok=True)` each `create_dirs` entry. Runs **after** the guard, right before `up`.
  - `compose_env(cfg: DockerConfig, worktree: Path, repo: Path) -> dict[str, str]`: `os.environ` plus `COMPOSE_PROJECT_NAME`, `COMPOSE_FILE=<worktree>/docker-compose.yml`, `COMPOSE_PROFILES=<profile>`, and `COMPOSE_ENV_FILES=<repo>/.env` (only if that file exists).
  - `up_command(cfg, worktree: Path, repo: Path) -> list[str]`: `["docker", "compose", "--project-name", P, "--project-directory", str(worktree), "--file", str(worktree / "docker-compose.yml"), *(["--env-file", str(repo / ".env")] if it exists), "--profile", profile, "up", "-d", "--wait", "--wait-timeout", str(up_timeout)]`.
  - `run_command(argv: list[str], *, cwd: Path, env: dict[str, str], timeout: int) -> tuple[str, str]`: returns `(status, output)`, same status strings as `verify._run_check`. **Move `_run_check` here** and import it in `verify.py`, so there is a single copy.
  - `runner_command(cfg, worktree: Path, line: str) -> list[str]`: `["sh", str(worktree / cfg.test_runner), *docker_args(line)]`.

- [ ] **Step 1: Write the failing tests**
  - `test_docker_config_defaults_to_none` and `test_docker_config_loads_project_name`: `{"docker": {"project_name": "dfs"}}` → `profile == "dyflexis"`, `up_timeout == 900`.
  - `test_docker_config_requires_project_name`: `{"docker": {}}` → `ValueError` matching `project_name`.
  - `test_guard_flags_changed_test_runner`: a real temp git repo; edit `test_runner.sh` → `["test_runner.sh"]`.
  - `test_guard_flags_ignored_env_file`: `.env` gitignored and created in the worktree → `[".env"]`.
  - `test_guard_flags_dockerfile_in_subfolder`: `legacy/docker/legacy-web/legacy-web.Dockerfile` changed → flagged.
  - `test_guard_ignores_normal_code`: only `legacy/src/Foo.php` changed → `[]`.
  - `test_compose_env_uses_main_env_file_not_worktree`: `repo/.env` exists → `COMPOSE_ENV_FILES == str(repo / ".env")`, and the up command contains `--env-file <repo>/.env`. No `.env` in repo → the key is absent.
  - `test_guard_skips_host_copies`: ignored `nginx-proxy/certs/ca.key` exists, `host_copies=("nginx-proxy/certs",)` → `[]`. Without `host_copies` → flagged.
  - `test_prepare_worktree_replaces_host_copy_and_creates_dirs`: the worktree has a stale `nginx-proxy/certs/x`; after the call it has exactly the main checkout's files, and `legacy/cache` exists.
  - `test_prepare_worktree_refuses_symlinked_target`: the worktree's `nginx-proxy/certs` is a symlink → `ValueError`.
  - `test_runner_command_builds_argv`: `runner_command(cfg, wt, "api FooCest") == ["sh", str(wt / "test_runner.sh"), "api", "FooCest"]`.
- [ ] **Step 2: Run, expect FAIL.**
- [ ] **Step 3: Implement** config + `docker_stack.py`.
- [ ] **Step 4: Run all tests, expect PASS** (the existing verify tests still pass after moving `_run_check`; update their `patch(...)` target to `claude_workflow.docker_stack.subprocess.run`).
- [ ] **Step 5:** `git add` the new files.

---

### Task 4: Per-ticket caches + Verify runs `tests.txt` and Docker

**Files:**
- Modify: `claude_workflow/sandbox.py`, `claude_workflow/stages/base.py`, `claude_workflow/stages/verify.py`
- Test: `tests/test_sandbox.py`, `tests/test_fix_loop.py`

**Interfaces:**
- Consumes: Tasks 1–3.
- Produces:
  - `SandboxSpec.cache_dir: Path | None = None`. When set, `build_bwrap_command` adds `--bind <cache_dir> /tmp/cw-cache` **after** `--tmpfs /tmp`, and `--setenv TMPDIR /tmp/cw-cache`.
  - `stage_cache_dir(config: WorkflowConfig, ticket: str, stage: StageName) -> Path`: returns `config.state_base / ".cache" / ticket / stage.value` and creates it. It lives **outside** the ticket's notes folder, so Implement cannot write Verify's cache.
  - `build_stage_sandbox` sets `cache_dir` for Implement and Verify only.
  - `SandboxSpec.repo_masks: tuple[str, ...] = ()`: repo-relative folders hidden with `--tmpfs <repo>/<path>` (only when the host folder exists, added after the repo bind). `build_stage_sandbox` fills it from `config.docker.host_copies` for **every** stage that mounts the worktree.

**Verify flow (replaces the body of `VerifyStage.run`):**
1. As today: refuse without a worktree or base; take `before = capture_diff(...)`.
2. Read `<state_dir>/tests.txt`.
   - **Missing** → write `06-verify.md` saying so, return **NEEDS_FIX** with "write tests.txt (see 04-plan.md)".
   - **Parse errors** → each one becomes a `FAIL (invalid line)` section.
3. Write `changed-files.txt` (from `changed_paths`) into the scratch notes dir. Build the env **once**: `sandbox_env(flake)` + `CW_CHANGED_FILES=<sandbox notes dir>/changed-files.txt`.
4. In the sandbox, run every `verify_commands` entry, then every `flake:` line.
5. If there are `docker:` lines:
   - `config.docker is None` → FAIL section "Docker not configured".
   - `guard_violations(..., host_copies=cfg.host_copies)` not empty → write the artifact, set `verified_diff`, return **FAILED** with "Docker tests skipped: the diff touches <paths>. Run them by hand." (the human decides; "continue anyway" works). **Changed in the final review:** this is now **NEEDS_HUMAN**, so the pipeline asks continue / retry / abort (see 09 "Built").
   - Else run `prepare_worktree`, then `up_command`. If it fails → a FAIL section; skip the lines.
   - Else run each line with `runner_command`, `cwd=worktree`, `env=compose_env(...)`, timeout `verify_timeout`.
6. Every section shows **status and full output**, passing or failing (decision 3).
7. Keep the existing "diff changed" check and the NEEDS_FIX / DONE logic.
8. **No `docker:` lines → never start the stack.**
9. **Empty `tests.txt`** → add a note "tests.txt lists no tests" to the artifact; not a failure.

- [ ] **Step 1: Write the failing tests**
  - `test_repo_masks_hide_folder_with_tmpfs` (sandbox): with `repo_masks=("nginx-proxy/certs",)` and that host folder present, the argv has `--tmpfs <sandbox repo>/nginx-proxy/certs` after the repo bind.
  - `test_cache_dir_is_bound_and_sets_tmpdir` (sandbox): the argv contains `--bind <cache> /tmp/cw-cache` after `--tmpfs /tmp`, and `--setenv TMPDIR /tmp/cw-cache`.
  - `test_stage_cache_dir_is_outside_state_dir`: the result is not inside `cfg.state_base / ticket`.
  - `test_verify_missing_tests_file_needs_fix`.
  - `test_verify_runs_flake_lines_in_sandbox`: `tests.txt` with one `flake:` line; patched `subprocess.run` is called with a bwrap argv ending in `["sh", "-c", "<line>"]`.
  - `test_verify_docker_guard_returns_failed_and_runs_no_docker`: patch `guard_violations` → `["test_runner.sh"]`; assert no call argv starts with `"docker"` or `"sh"` + `test_runner.sh`.
  - `test_verify_without_docker_lines_never_starts_stack`.
  - `test_verify_runs_docker_line_after_up`: patched runs succeed; the call order is `up` then `sh <wt>/test_runner.sh api FooCest`.
  - `test_verify_artifact_shows_passing_output`: a passing command's stdout appears in `06-verify.md`.
  - Update `_verify_ctx` in `test_fix_loop.py` to write a `tests.txt`.
- [ ] **Step 2: Run, expect FAIL.**
- [ ] **Step 3: Implement.** Keep `VerifyStage.run` short: put the sandbox part and the Docker part in two helper functions in `verify.py` (`_run_sandbox_checks`, `_run_docker_checks`), each returning `(sections: list[str], all_passed: bool)`.
- [ ] **Step 4: Run all tests, expect PASS.**

---

### Task 5: Plan, Implement and Review prompts + skills

**Files:**
- Modify: `claude_workflow/stages/plan.py`, `claude_workflow/stages/implement.py`, `claude_workflow/stages/review.py`
- Modify: `skills/plan/SKILL.md`, `skills/implement/SKILL.md`, `skills/review/SKILL.md`
- Test: `tests/test_fix_loop.py` (prompt tests), plus a review test

**What changes:**
- **Plan draft prompt:** "Also write `<notes>/tests.txt`: one line per test to run, `flake: <command>` or `docker: <test_runner.sh arguments>`. List every test you plan to create or edit." The **reviewer prompt** also checks `tests.txt`.
- **Implement prompt** (replaces `_test_first_instruction`):
  - "Run the `flake:` lines from `tests.txt`. `docker:` lines run only in Verify."
  - "If you add or rename a test, update `tests.txt`."
  - "Verify always runs: `<verify_commands>`. You may run them yourself on the files you changed."
- **Review:**
  - Correctness lens prompt: "If you think a test will fail, append it to `<notes>/tests.txt` under `# suggested by review` and report it as a finding."
  - In `ReviewStage.run`: hash `tests.txt` before the lenses and after them. If it changed → **NEEDS_FIX** (also when both lenses approved), with the message "Review suggested tests in tests.txt".
- **Skills:**
  - Plan + Implement: the `tests.txt` format and the **migrations rule** (see Global Constraints; say "the human runs the migration" in `05-implement.md`).
  - Review: the `# suggested by review` rule.

- [ ] **Step 1: Write the failing tests**
  - `test_plan_prompt_asks_for_tests_file`: the draft prompt contains `tests.txt`.
  - `test_implement_prompt_points_to_tests_file`: contains `tests.txt` and `flake:`.
  - Update `test_implement_prompt_*` that expect "Check commands" text.
  - `test_review_test_suggestion_forces_fix_round`: a stubbed `run_claude_headless` writes both lens files with `APPROVED` and appends a line to `tests.txt` → `NEEDS_FIX`.
- [ ] **Step 2: Run, expect FAIL.**
- [ ] **Step 3: Implement** the prompts, the review check and the skill text.
- [ ] **Step 4: Run all tests, expect PASS.**

---

### Task 6: Monorepo config, docs, and the Nix build

**Files:**
- Modify: `roles/ai/configuration/workflows/config.json`
- Modify: `roles/ai/docs/04-file-responsibilities.md`, `roles/ai/docs/08-next-session.md`, `roles/ai/docs/09-tests-and-docker.md`

**Config values:**

```json
"flake_path": "~/.dotfiles/templates/latest",
"verify_commands": [
  "cd legacy && files=$(sed -n 's#^legacy/##p' \"$CW_CHANGED_FILES\" | grep '\\.php$' || true); if [ -z \"$files\" ]; then echo 'no changed PHP files'; else vendor/bin/phpstan analyze --memory-limit=-1 --no-progress -c phpstan.neon.dist $files; fi"
],
"shared_dependencies": [
  { "dir": "legacy/vendor", "lockfile": "legacy/composer.lock" },
  { "dir": "legacy/app/node_modules", "lockfile": "legacy/app/pnpm-lock.yaml" },
  { "dir": "frontend/node_modules", "lockfile": "frontend/pnpm-lock.yaml" },
  { "dir": "tools/vendor", "lockfile": "tools/composer.lock" }
],
"docker": {
  "project_name": "dyflexis-monorepo",
  "profile": "dyflexis",
  "host_copies": ["nginx-proxy/certs"],
  "create_dirs": ["legacy/cache"]
}
```

- [ ] **Step 1:** Fill in the config (`project_name` confirmed by the user via `docker compose ls`).
- [ ] **Step 2:** Add a test in `tests/test_config.py` that loads the real `config.json` without errors.
- [ ] **Step 3:** Update the docs: new modules in `04`, status in `08`, "built" in `09`.
- [ ] **Step 4:** Run all unit tests, then the Nix build the way the previous phase did (see `08-next-session.md`). Expect PASS.
- [ ] **Step 5: Stop and ask the user to review and commit.**

---

### Task 7: First real checks (with the user)

These touch the user's real Docker stack. **Confirm each Docker step with the user before running it.**

- [ ] **Step 1: flake lines in the sandbox.** Open a sandbox shell as in `08-next-session.md`, then run `cd legacy/app && pnpm run test` and `cd frontend && pnpm run test:unit`. Expect both to run (pass or fail is fine; they must start).
- [ ] **Step 2: phpstan cache.** Run phpstan twice with `TMPDIR` set to a kept folder. Expect `$TMPDIR/phpstan` to exist and the second run to be faster. If not: find phpstan's real cache path and change `TMPDIR` to a `tmpDir` approach.
- [ ] **Step 3: compose.** Run `up_command` by hand for a worktree. Check that `--wait` returns with the one-shot services, that `test_runner.sh unit` works with `COMPOSE_ENV_FILES`, and where `HOST_UID` comes from.
  - **Check the untracked folders.** `nginx-proxy/certs` is copied by `prepare_worktree` and `legacy/cache` is created by it. Confirm the proxy starts with the copied certs and the app rebuilds `legacy/cache`. Also confirm the certs are hidden in a sandbox shell (`ls nginx-proxy/certs` is empty).
  - **Cert keys are `root:root 0600`**, so the copy fails today. **User decision:** copy through a root Docker container, or copy only `*.crt` (see 09 "Known limits").
  - **Check `git status` stays clean after `up`** in a fresh worktree. The containers run `pnpm install` and webpack, which might touch tracked files. If they do, Verify stops with "Verification changed the worktree diff".
- [ ] **Step 4:** Write the results in `09-tests-and-docker.md` ("Still to confirm"), and fix the code if a check failed.
- [ ] **Step 5:** Ask the user whether to start a full run on a real ticket.
