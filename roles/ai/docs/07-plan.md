# claude-workflow fixes — Implementation Plan

> **Status (2026-11-19):** all tasks done (checkboxes were never ticked). See `08-next-session.md` for the current status.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** fix the bugs in `06-bugs.md` and add the features from our Q&A: shared dependencies, a clean sandbox environment, skills as a system prompt, TDD in Implement, and an automatic fix loop.

**Architecture:** same design as now (Python orchestrator → bwrap → `claude`). It adds two small modules (`deps.py`, `env.py`). The ticket worktree is created **at Explore** instead of at Implement, so every stage sees the same code.

**Tech Stack:** Python 3.12 (stdlib only), bubblewrap, git, Nix, Claude Code 2.1.322.

**Spec:** `roles/ai/docs/06-bugs.md` + our conversation (questions 1–7).

---

## Decisions for you (my default in bold)

These change what gets built. I'll use the default unless you say otherwise.

| # | Question | Default | Why |
|---|---|---|---|
| D1 | Which Atlassian MCP do you use? A server named `atlassian` in `~/.claude.json`, or the **claude.ai "Atlassian Rovo" connector**? | **Keep `atlassian`**, make the name configurable (Task 15) | I can't see your setup. The connector has different tool names (`mcp__claude_ai_Atlassian_Rovo__*`). |
| D2 | Should Finalize skip git hooks (`git commit --no-verify`)? | **Yes, skip** | Verify already ran your checks. A formatting hook would break the "diff must not change" check. The commit is local and CI still runs on push. |
| D3 | Mount your personal `~/.claude/CLAUDE.md` in the sandbox? | **Yes, read-only** | Your formatting rules (dyslexia) then also apply to artifacts and interactive stages. |
| D4 | How many fix rounds (Verify/Review → Implement) before stopping? | **3** | Same idea as `max_plan_reviews`. It's configurable. |


Answers, when it's different from your default:
D1 = Atlassian-Rovo-MCP
---

## Global Constraints

- **One ticket at a time.** No parallel runs or multi-ticket features.
- **Skill content stays unchanged.** Only *how* skills reach Claude changes (Task 6). You'll rework the content later.
- **Web server / database for integration, API and e2e tests is out of scope.** We'll discuss it next.
- Python **≥ 3.12**, **stdlib only** (`dependencies = []` in `pyproject.toml`).
- Code style: ruff (line length **100**), pyright **strict**, as in `pyproject.toml`.
- The host never runs `git push`, `fetch` or `pull`.
- I only commit **after you OK it** (your settings ask before `git commit`).
- Working dir for all commands: `roles/ai/configuration/workflows/workflow/`.
- Test command (called **`$PYTEST`** below):

```sh
nix shell --impure --expr 'with import (builtins.getFlake "nixpkgs") {}; [ (python312.withPackages (p: [p.pytest])) git ]' -c python -m pytest -q -p no:cacheprovider
```

---

## Overview: change → bug/question → task

| Task | Change | Fixes |
|---|---|---|
| 1 | Repo = git root, ticket key upper case | M1, M3 |
| 2 | Create worktree at Explore; every stage uses it | M2, L3 |
| 3 | Mount `vendor/` + `node_modules/` read-only from main checkout | H2, Q3 |
| 4 | Clean sandbox env; load dev shell once | M6, L7 |
| 5 | Interactive stages get a real terminal | H1 |
| 6 | Skills as system prompt; sandbox settings without hooks; `CLAUDE.md` | Q4, L1, L5, D3 |
| 7 | Blocker file fixes | H3, H4 |
| 8 | Lenient verdict parsing | H5 |
| 9 | Automatic fix loop Verify/Review → Implement | Q7, L4, flow notes |
| 10 | TDD instructions in Plan and Implement prompts | Q1 |
| 11 | Timeouts; clearer "verify changed the diff" message | M8, M5 |
| 12 | Proxy allows token refresh; proxy log; one credentials file | H6 |
| 13 | Finalize commit without hooks | M4, D2 |
| 14 | Nix cleanup, `sandbox_shell.py` update, docs update | L6 |
| 15 | Configurable Atlassian MCP check | M7, D1 |

**Not fixing: L2** (an escalation during plan revision restarts Plan). Fixing it means resumable plan state, which is more code than the problem is worth. The cost is one extra draft run.

---

## Review Focus

Inputs most likely to bite you that the obvious tests miss. Each has a test in its task.

1. **Main checkout moved between runs** (you switched branch after Explore). Expected: the ticket keeps its original base commit. → Task 2, `test_worktree_base_is_fixed_after_first_creation`.
2. **A lockfile missing on one side** (e.g. no `package-lock.json` in the worktree, but one in main). Expected: a clear mismatch error, not a silent mount. → Task 3, `test_lockfile_missing_on_one_side_is_mismatch`.
3. **`nix develop` fails** (broken flake). Expected: the stage fails with nix's error, not an empty environment. → Task 4, `test_dev_shell_env_failure_raises`.
4. **`--only-stage review` asks for a fix.** Expected: the feedback is saved, and the run stops and tells you to run `--from-stage implement`, which keeps that feedback. → Task 9, `test_only_stage_fix_choice_keeps_feedback_for_from_stage_implement`.
5. **Verdict written as `Approved` or `CHANGES REQUESTED` (with a space).** Expected: accepted. → Task 8 parametrized cases.

---

### Task 1: Repo root and ticket key normalization

**Why:** running from a subfolder now mounts only that subfolder, and resuming from another folder fails (M1). `proj-123` and `PROJ-123` create two states that share one branch (M3).

**Files:**
- Modify: `claude_workflow/git_host.py` (add function)
- Modify: `claude_workflow/cli.py:51-62`
- Modify: `claude_workflow/pipeline.py:125-129`
- Test: `tests/test_git_host.py`, `tests/test_workflow_regressions.py`

**Interfaces:**
- Produces: `git_host.repo_root(path: Path) -> Path` (raises `GitError` if not a git repo).
- Produces: `run_pipeline` uses `ticket_id.upper()` everywhere after validation.

- [ ] **Step 1: Write failing tests**

```python
def test_repo_root_returns_toplevel_from_subdir(tmp_path):
    repo = _init_repo(tmp_path)          # existing helper in test_git_host.py
    (repo / "sub").mkdir()
    assert repo_root(repo / "sub") == repo.resolve()

def test_repo_root_outside_git_raises(tmp_path):
    with pytest.raises(GitError):
        repo_root(tmp_path)

def test_lowercase_ticket_uses_uppercase_state_dir(self):
    # run_pipeline("proj-1", config with state_base=tmp, stub runners) →
    assert (tmp / "PROJ-1").is_dir() and not (tmp / "proj-1").exists()
```

- [ ] **Step 2: Run, expect FAIL** — `$PYTEST tests/test_git_host.py tests/test_workflow_regressions.py` → `ImportError: repo_root` / assertion error.
- [ ] **Step 3: Implement**
  - `repo_root`: `git rev-parse --show-toplevel`.
  - In `cli.main`: `config = replace(config, repo_path=repo_root(config.repo_path))`. Report a `GitError` via `parser.error`.
  - In `run_pipeline`: `ticket_id = ticket_id.upper()` right after the regex check.
- [ ] **Step 4: Run, expect PASS** — `$PYTEST`
- [ ] **Step 5: Commit** — `fix(workflow): resolve repo root and normalize ticket key`

---

### Task 2: Worktree from Explore on

**Why:** Explore/Plan read your main checkout's working tree, but Implement branches from `HEAD` later, so the plan can describe different code (M2). Implement's escalation Q&A looks at the main checkout instead of the new code (L3). With one worktree from the start, **every stage sees the same code**, and your main checkout stays free to use.

**Files:**
- Modify: `claude_workflow/stages/base.py` (add function)
- Modify: `claude_workflow/stages/explore.py`, `qa.py`, `plan.py`, `implement.py:24-39`
- Modify: `claude_workflow/pipeline.py:67-73` (escalation uses worktree)
- Test: `tests/test_workflow_regressions.py`

**Interfaces:**
- Produces: `base.ensure_ticket_worktree(ctx: StageContext) -> Path`. Creates or reuses the worktree, sets `state.worktree_path/branch_name/base_commit` once, saves state, returns the worktree path. If the main checkout is dirty at **first** creation, it prints: `Warning: uncommitted changes in <repo> are not part of the ticket worktree.`
- Consumes: `git_host.ensure_worktree`, `rev_parse_head`, `is_dirty` (unchanged).

- [ ] **Step 1: Write failing tests**

```python
def test_explore_mounts_ticket_worktree_not_main_checkout(self):
    # patch run_claude_headless, capture sandbox spec
    assert spec.repo_dir == config.worktree_base / "PROJ-1"

def test_worktree_base_is_fixed_after_first_creation(self):
    # create worktree, commit something new in main repo, call again
    assert state.base_commit == first_head
```

- [ ] **Step 2: Run, expect FAIL** — `$PYTEST tests/test_workflow_regressions.py`
- [ ] **Step 3: Implement** — move lines `implement.py:24-39` into `ensure_ticket_worktree`. Call it in Explore, Q&A, Plan, Implement and `_run_escalation_qa`, and pass its result as `repo_dir` and `workdir`. Explore, Q&A and Plan keep `repo_access: ro`.
- [ ] **Step 4: Run, expect PASS** — `$PYTEST`
- [ ] **Step 5: Commit** — `feat(workflow): create ticket worktree at explore`

---

### Task 3: Shared dependencies (`vendor/`, `node_modules/`)

**Why:** a fresh worktree has no `vendor/` or `node_modules/`, and the sandbox has no network, so tests can't run (H2). Mounting the main checkout's folders **read-only** costs nothing and can't damage them. The lockfile check makes sure they fit the worktree's code.

**Rules** (in this order, per dependency):

1. The worktree has its **own non-empty** folder → use it, don't mount.
2. Lockfile differs between main and worktree (missing on **one** side counts as different) → **fail** with: `<lockfile> differs from <main>. Run the install in <worktree>/ on the host, then rerun.`
3. The main folder doesn't exist → skip silently.
4. Otherwise: create an empty `<worktree>/<dir>` mount point on the host and mount `<main>/<dir>` read-only there.

**Files:**
- Create: `claude_workflow/deps.py`
- Modify: `claude_workflow/config.py` (new key), `configuration/workflows/config.json`
- Modify: `claude_workflow/sandbox.py` (`SandboxSpec` field, bwrap binds)
- Modify: `claude_workflow/stages/base.py:60-85` (`build_stage_sandbox`)
- Test: create `tests/test_deps.py`; modify `tests/test_sandbox.py`

**Interfaces:**
- Produces: `@dataclass(frozen=True) class SharedDependency: dir: str; lockfile: str`
- Produces: `class DependencyMismatch(ValueError)`
- Produces: `deps.resolve_shared_dependencies(main_repo: Path, worktree: Path, deps: tuple[SharedDependency, ...]) -> tuple[tuple[Path, str], ...]` — returns `(host_dir, repo_relative_target)` pairs.
- Produces: `WorkflowConfig.shared_dependencies: tuple[SharedDependency, ...]`. The code default is `()`. `config.json` sets `[{"dir": "vendor", "lockfile": "composer.lock"}, {"dir": "node_modules", "lockfile": "package-lock.json"}]`.
- Produces: `SandboxSpec.repo_ro_overlays: tuple[tuple[Path, str], ...] = ()` → bwrap `--ro-bind <host> <repo_target>/<rel>`, added **after** the repo bind and `.git` mask.

- [ ] **Step 1: Write failing tests** (`tests/test_deps.py`)

```python
def test_mounts_main_dir_when_lockfiles_match(tmp_path):        # → [(main/"vendor", "vendor")]
def test_creates_empty_mountpoint_in_worktree(tmp_path):        # (worktree/"vendor").is_dir()
def test_worktree_own_dir_is_used_instead(tmp_path):            # → ()
def test_lockfile_differs_raises(tmp_path):                     # pytest.raises(DependencyMismatch)
def test_lockfile_missing_on_one_side_is_mismatch(tmp_path):    # pytest.raises(DependencyMismatch)
def test_missing_main_dir_is_skipped(tmp_path):                 # → ()
```

and in `tests/test_sandbox.py`:

```python
def test_bwrap_ro_binds_repo_overlays_after_repo(tmp_path, monkeypatch):
    # spec.repo_ro_overlays=((main/"vendor", "vendor"),)
    i = cmd.index(str(main / "vendor"))
    assert cmd[i-1] == "--ro-bind" and cmd[i+1].endswith("/vendor")
    assert i > cmd.index(str(spec.repo_dir))
```

- [ ] **Step 2: Run, expect FAIL** — `$PYTEST tests/test_deps.py tests/test_sandbox.py`
- [ ] **Step 3: Implement** the rules above. In `build_stage_sandbox`, call the resolver when `repo_dir` is the ticket worktree. Validate the config key: a list of objects with non-empty string `dir` and `lockfile`.
- [ ] **Step 4: Run, expect PASS** — `$PYTEST`
- [ ] **Step 5: Manual check (needs a Dyflexis repo)** — `grep -c "$HOME" vendor/composer/autoload_static.php` should print `0` (autoload uses relative paths). Then open `tools/sandbox_shell.py implement` and run one unit test.
- [ ] **Step 6: Commit** — `feat(workflow): share vendor and node_modules read-only`

---

### Task 4: Clean sandbox environment and one-time dev shell

**Why:** bwrap passes **all** your environment variables (tokens included) into the sandbox, and 3 stages have full internet (M6). Also, `nix develop` runs again for every Claude call and every verify command (L7).

**How:** start bwrap with `--clearenv` and set only:

- an **allowlist** of host variables: `HOME USER LOGNAME PATH SHELL LANG LC_ALL LC_CTYPE TERM COLORTERM TZ NIX_SSL_CERT_FILE SSL_CERT_FILE`;
- plus, if `flake_path` is set, **every variable the dev shell adds or changes**. These are captured **once per process** by running `nix develop <flake> --command env -0`, so `shellHook` exports are included.

This replaces `_wrap_with_flake`: no more `nix develop` around bwrap.

**Files:**
- Create: `claude_workflow/env.py`
- Modify: `claude_workflow/sandbox.py:164-240` (`build_bwrap_command`)
- Modify: `claude_workflow/claude_runner.py:63-66, 88-90, 126-128` (remove flake wrap, pass env)
- Modify: `claude_workflow/stages/verify.py:46-55`
- Test: create `tests/test_env.py`; modify `tests/test_sandbox.py`, `tests/test_claude_runner.py`

**Interfaces:**
- Produces: `env.HOST_ENV_ALLOWLIST: tuple[str, ...]` (values above)
- Produces: `env.sandbox_env(flake: Path | None) -> dict[str, str]`
- Produces: `env.dev_shell_env(flake: Path) -> dict[str, str]`, cached with `functools.cache`. Raises `RuntimeError(f"nix develop {flake} failed: {stderr}")` on a non-zero exit.
- Changes: `build_bwrap_command(spec, inner_cmd, *, env: Mapping[str, str]) -> list[str]` emits `--clearenv` and then `--setenv K V` per item.

- [ ] **Step 1: Write failing tests** (`tests/test_env.py`)

```python
def test_sandbox_env_drops_unlisted_host_vars(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "x"); monkeypatch.setenv("TERM", "xterm")
    env = sandbox_env(None)
    assert "GITHUB_TOKEN" not in env and env["TERM"] == "xterm"

def test_sandbox_env_adds_dev_shell_changes(monkeypatch):
    # patch subprocess.run → stdout "PATH=/nix/store/php/bin\0PHP_INI_SCAN_DIR=/x\0GITHUB_TOKEN=x\0"
    # with host GITHUB_TOKEN=x (unchanged → dropped)
    assert env["PHP_INI_SCAN_DIR"] == "/x" and env["PATH"] == "/nix/store/php/bin"
    assert "GITHUB_TOKEN" not in env

def test_dev_shell_env_runs_nix_once(monkeypatch):     # 2 calls → subprocess.run called once
def test_dev_shell_env_failure_raises(monkeypatch):    # returncode 1 → RuntimeError, "nix develop" in msg
```

and in `test_sandbox.py`: `assert "--clearenv" in cmd` and `cmd[cmd.index("--setenv")+1:][:2] == ["HOME", ...]`.

- [ ] **Step 2: Run, expect FAIL** — `$PYTEST tests/test_env.py`
- [ ] **Step 3: Implement.** The variables from the proxy bridge script (`HTTPS_PROXY` …) are still exported inside by the `sh` wrapper, so no change is needed there. Update the existing runner tests that expect `nix develop` in argv.
- [ ] **Step 4: Run, expect PASS** — `$PYTEST`
- [ ] **Step 5: Commit** — `feat(workflow): clear sandbox env and load dev shell once`

---

### Task 5: Real terminal for interactive stages

**Why:** `--new-session` removes the controlling terminal (verified: `tty_nr=0`, `/dev/tty` fails). Resize, Ctrl-C and tools that need `/dev/tty` break (H1). The flag protects against TIOCSTI injection, which this kernel already blocks (`legacy_tiocsti = 0`).

**Files:**
- Modify: `claude_workflow/sandbox.py` (`build_bwrap_command`)
- Modify: `claude_workflow/claude_runner.py:100-130`
- Test: `tests/test_sandbox.py`

**Interfaces:**
- Changes: `build_bwrap_command(spec, inner_cmd, *, env, interactive: bool = False)`.
- Produces: `sandbox.tiocsti_disabled() -> bool` — reads `/proc/sys/dev/tty/legacy_tiocsti`; `True` only if the content is `"0"`.
- Rule: leave out `--new-session` only when `interactive and tiocsti_disabled()`. Otherwise keep it, and for interactive runs print `Warning: TIOCSTI enabled; interactive sandbox has no controlling terminal.`

- [ ] **Step 1: Write failing tests**

```python
def test_interactive_omits_new_session_when_tiocsti_disabled(monkeypatch):  # patch tiocsti_disabled→True
def test_interactive_keeps_new_session_when_tiocsti_enabled(monkeypatch):   # →False: "--new-session" in cmd
def test_headless_keeps_new_session(monkeypatch):                            # interactive=False
```

- [ ] **Step 2: Run, expect FAIL** — `$PYTEST tests/test_sandbox.py`
- [ ] **Step 3: Implement**; `run_claude_interactive` passes `interactive=True`.
- [ ] **Step 4: Run, expect PASS** — `$PYTEST`
- [ ] **Step 5: Manual check** — `sandbox_shell.py qa --interactive -- sh -c 'cut -d" " -f7 /proc/self/stat'` prints non-zero. Then `-- claude`: resize the window and press Ctrl-C twice; the exit code is printed.
- [ ] **Step 6: Commit** — `fix(workflow): keep controlling terminal for interactive stages`

---

### Task 6: Skills as system prompt, safe settings, personal CLAUDE.md

**Why:**

- Skills now only reach Claude through "first read SKILL.md" in the prompt. Claude may skip the read. **`--append-system-prompt`** makes the rules always-on and keeps Claude Code's default prompt (Q4).
- Mounting skills into `~/.claude/skills` also leaves empty folders of other stages behind (L1). With the system prompt, **the skills mount can go**.
- Your `settings.json` hooks call `notify-send`, which fails in the sandbox (L5). A generated copy **without `hooks`**, mounted read-only, keeps your deny rules and `env`.
- D3: mount `~/.claude/CLAUDE.md` read-only.
- Retro proposes skill changes, so it gets **all skills read-only** at `~/skills`.

**Files:**
- Modify: `claude_workflow/stages/base.py:88-100` (replace `skill_prompt_prefix`)
- Modify: all `claude_workflow/stages/*.py` that use `skill_prompt_prefix`
- Modify: `claude_workflow/claude_runner.py:29-51`
- Modify: `claude_workflow/sandbox.py:92-93, 198-206, 226-229`
- Test: `tests/test_claude_runner.py`, `tests/test_sandbox.py`, `tests/test_workflow_regressions.py`

**Interfaces:**
- Produces: `base.stage_system_prompt(config: WorkflowConfig, stage: StageName) -> str` — `shared` then `<stage>` `SKILL.md` contents, YAML front matter removed, joined by `"\n\n"`; `""` if neither exists.
- Changes: `run_claude_headless(..., system_prompt: str = "")` and `run_claude_interactive(..., system_prompt: str = "")` → `--append-system-prompt <text>` when non-empty.
- Changes: `run_headless_with_escalation` builds the system prompt from `stage` and passes it on.
- Produces: `sandbox.sandbox_settings(host_settings: Path) -> dict[str, object]` — the host JSON without the `"hooks"` key, or `{}` if missing.
- Produces: `SandboxSpec.settings_file: Path | None` (written by the runner into a `TemporaryDirectory`, ro-bound to `~/.claude/settings.json`). It is **not** written into the state dir, because Claude can write there.
- Produces: `SandboxSpec.home_ro_mounts: tuple[tuple[Path, str], ...] = ()` — `(host, home-relative target)`. Used for `~/.claude/CLAUDE.md` (all stages) and `skills_base → "skills"` (Retro only).
- Removes: the `SandboxPaths.skills_dir` mount and the `--add-dir` for skills.

- [ ] **Step 1: Write failing tests**

```python
def test_stage_system_prompt_strips_front_matter(tmp_path):
    # shared/SKILL.md "---\nname: shared\n---\n# Shared\nrule" ; plan/SKILL.md similar
    assert p.startswith("# Shared") and "name: shared" not in p and "# Plan" in p

def test_headless_passes_append_system_prompt():   # "--append-system-prompt" followed by text
def test_bwrap_does_not_mount_skills():             # no arg ends with "/.claude/skills/..."
def test_sandbox_settings_drops_hooks(tmp_path):    # {"hooks":{..},"permissions":{..}} → no "hooks"
def test_retro_mounts_all_skills_read_only():       # ("--ro-bind", skills_base, home/"skills")
def test_claude_md_is_mounted_read_only():          # ("--ro-bind", host CLAUDE.md, home/".claude/CLAUDE.md")
```

- [ ] **Step 2: Run, expect FAIL** — `$PYTEST`
- [ ] **Step 3: Implement.** Stage prompts lose their prefix and keep only the task text. Update `test_bwrap_mounts_only_stage_skills_kb_and_flake`, which now has to assert that skills are **not** mounted.
- [ ] **Step 4: Run, expect PASS** — `$PYTEST`
- [ ] **Step 5: Commit** — `feat(workflow): pass skills as system prompt, drop hooks in sandbox`

---

### Task 7: Blocker file fixes

**Why:** the plan reviewer's `blocked-questions.md` is ignored and then blocks Implement (H3). An empty blocker file blocks the ticket forever (H4).

**Files:**
- Modify: `claude_workflow/stages/base.py:103-175`
- Modify: `claude_workflow/stages/plan.py:62-73`
- Modify: `claude_workflow/pipeline.py:222-226`
- Test: `tests/test_pipeline.py`

**Interfaces:**
- Produces: `base.has_blocker(state_dir: Path) -> bool` — `True` if `blocked-questions.md` has non-whitespace content. If the file exists but is empty: delete it and return `False`.
- Used in: `run_headless_with_escalation`, the Plan review pass (after `run_claude_headless`, before the verdict), and `pipeline.py:223`.

- [ ] **Step 1: Write failing tests**

```python
def test_plan_review_blocker_returns_blocked(...):   # reviewer writes blocker → BLOCKED_QUESTIONS
def test_empty_blocker_is_removed_and_stage_runs(...):
    # empty blocked-questions.md before Plan → runner called, file gone
```

- [ ] **Step 2: Run, expect FAIL** — `$PYTEST tests/test_pipeline.py`
- [ ] **Step 3: Implement**
- [ ] **Step 4: Run, expect PASS** — `$PYTEST`
- [ ] **Step 5: Commit** — `fix(workflow): handle reviewer and empty blocker files`

---

### Task 8: Lenient verdict parsing

**Why:** a first line like `# APPROVED` or `**APPROVED**` now gives "Invalid verdict" (H5).

**Files:**
- Modify: `claude_workflow/stages/base.py` (add function)
- Modify: `claude_workflow/stages/plan.py:74-78`, `claude_workflow/stages/review.py:85-87`
- Test: `tests/test_workflow_regressions.py`

**Interfaces:**
- Produces: `base.parse_verdict(text: str) -> Literal["APPROVED", "CHANGES_REQUESTED"] | None`. It looks at the first non-empty line, strips `#*_`>` and spaces at both ends and trailing `.:!`, upper-cases it, and replaces spaces with `_`. It then matches exactly or as a prefix followed by a non-letter.

- [ ] **Step 1: Write failing test**

```python
@pytest.mark.parametrize("text,expected", [
    ("APPROVED", "APPROVED"), ("# APPROVED", "APPROVED"), ("**APPROVED**", "APPROVED"),
    ("APPROVED.", "APPROVED"), ("\n\nApproved", "APPROVED"),
    ("CHANGES_REQUESTED", "CHANGES_REQUESTED"), ("## Changes requested", "CHANGES_REQUESTED"),
    ("CHANGES_REQUESTED: fix x", "CHANGES_REQUESTED"),
    ("NOT APPROVED", None), ("Looks good", None), ("APPROVEDISH", None), ("", None),
])
def test_parse_verdict(text, expected): assert parse_verdict(text) == expected
```

- [ ] **Step 2: Run, expect FAIL** — `$PYTEST tests/test_workflow_regressions.py`
- [ ] **Step 3: Implement**; Plan and Review use it (`None` → FAILED "Invalid verdict", as now).
- [ ] **Step 4: Run, expect PASS** — `$PYTEST`
- [ ] **Step 5: Commit** — `fix(workflow): accept markdown-decorated verdicts`

---

### Task 9: Automatic fix loop (Verify/Review → Implement)

**Why:** now a failing Verify or a "changes requested" Review stops the run, and you must remember `--from-stage implement` (Q7). Implement also reads an old `07-review.md` even after re-planning (L4). This adds a **capped loop**, like the plan review loop.

**Behavior:**

- Verify (a command fails) and Review (any lens `CHANGES_REQUESTED`) return the new outcome **`NEEDS_FIX`**.
- Verify still stores `verified_diff` before returning `NEEDS_FIX`, so "continue anyway" works.
- Without `--auto`, the pipeline asks: `[<stage>] needs fixes (round n/max): [f]ix in Implement / [c]ontinue anyway / [a]bort`. `f` is only offered while `fix_rounds < max_fix_rounds`.
- With `--auto`: `f` while rounds are left, otherwise exit 1 with `<stage> still needs fixes after <max> rounds`.
- `f`: `fix_feedback = <artifact name>`, `fix_rounds += 1`. Implement and later stages are un-completed, `verified_diff = None`, Implement's session and escalation count are dropped, and the run jumps to Implement.
- `c`: mark the stage completed, then go to the next stage (no extra gate).
- `a`: exit 1; a rerun repeats the stage.
- In `--only-stage` mode, `f` saves the feedback and stops with: `Run: claude-workflow <T> --from-stage implement`.
- Implement prompt: if `fix_feedback` is set → `Fix the problems listed in ~/notes/<fix_feedback>.` The old automatic `07-review.md` read is **removed**.
- `fix_feedback` is cleared when Implement is marked completed.
- `--from-stage X`: if X is **before** Implement, reset `fix_rounds = 0` and `fix_feedback = None`. If X is Implement, keep the feedback and reset `fix_rounds = 0`.

**Files:**
- Modify: `claude_workflow/stages/base.py:17-22` (enum)
- Modify: `claude_workflow/state.py` (2 fields, load/save)
- Modify: `claude_workflow/config.py` (`max_fix_rounds`, default **3**, ≥ 0), `configuration/workflows/config.json`
- Modify: `claude_workflow/pipeline.py` (new branch in the loop, new `_prompt_fix`)
- Modify: `claude_workflow/stages/verify.py:63-79`, `review.py:93-96`, `implement.py:49-64`
- Test: create `tests/test_fix_loop.py`

**Interfaces:**
- Produces: `StageOutcome.NEEDS_FIX = "needs_fix"`
- Produces: `TicketState.fix_rounds: int = 0`, `TicketState.fix_feedback: str | None = None`
- Produces: `WorkflowConfig.max_fix_rounds: int`
- Produces: `pipeline._prompt_fix(stage: StageName, rounds: int, max_rounds: int) -> Literal["f", "c", "a"]`

- [ ] **Step 1: Write failing tests** (stub runners, like `test_pipeline.py`)

```python
def test_review_needs_fix_returns_to_implement_with_feedback(...):
    # review returns NEEDS_FIX once then DONE; auto=True
    assert calls == [..., IMPLEMENT, VERIFY, REVIEW, IMPLEMENT, VERIFY, REVIEW, RETRO]
    assert state_after_first_fix.fix_feedback == "07-review.md"

def test_fix_loop_stops_after_max_fix_rounds(...):      # always NEEDS_FIX, max=2 → rc 1, 2 extra implements
def test_continue_anyway_skips_to_next_stage(...):     # input "c" → next runner is REVIEW
def test_from_stage_plan_clears_fix_feedback(...):
def test_only_stage_fix_choice_keeps_feedback_for_from_stage_implement(...):
def test_implement_prompt_mentions_feedback_only_when_set(...):
def test_verify_failure_returns_needs_fix_and_sets_verified_diff(...):
```

- [ ] **Step 2: Run, expect FAIL** — `$PYTEST tests/test_fix_loop.py`
- [ ] **Step 3: Implement** the behavior above. Update `test_pipeline.py` / regression tests that expect FAILED from Review or Verify.
- [ ] **Step 4: Run, expect PASS** — `$PYTEST`
- [ ] **Step 5: Commit** — `feat(workflow): capped fix loop from verify and review to implement`

---

### Task 10: TDD instructions in Plan and Implement

**Why:** Implement can run tests now (Tasks 3 and 4), but nothing tells it to work test-first (Q1). This goes in the **stage prompt in code**, so the skills stay untouched until you rework them.

**Files:**
- Modify: `claude_workflow/stages/plan.py:40-46`, `claude_workflow/stages/implement.py:57-64`
- Test: `tests/test_workflow_regressions.py`

**Interfaces:**
- Plan draft prompt adds: `Write the plan test-first: each step names the test to write before the code it covers.`
- Implement prompt adds: `Work test-first: for each plan step, write the test, run it and see it fail, then write the code until it passes. Check commands: <"; ".join(verify_commands)>. You may run a single test file with the same tools.` The command list is left out when `verify_commands` is empty.

- [ ] **Step 1: Write failing test**

```python
def test_implement_prompt_is_test_first_with_commands(...):
    # verify_commands=("vendor/bin/phpunit",) ; capture prompt via patched run_headless_with_escalation
    assert "test-first" in prompt and "vendor/bin/phpunit" in prompt
```

- [ ] **Step 2: Run, expect FAIL** — `$PYTEST tests/test_workflow_regressions.py`
- [ ] **Step 3: Implement**
- [ ] **Step 4: Run, expect PASS** — `$PYTEST`
- [ ] **Step 5: Commit** — `feat(workflow): ask plan and implement to work test-first`

---

### Task 11: Timeouts and a clearer Verify message

**Why:** a hanging test or a stuck headless Claude hangs the workflow forever (M8). "Verification changed the worktree diff" doesn't say **which files** changed (M5).

**Files:**
- Modify: `claude_workflow/config.py`, `configuration/workflows/config.json`
- Modify: `claude_workflow/claude_runner.py:90`, `claude_workflow/stages/verify.py:56, 70-73`
- Modify: `claude_workflow/git_host.py` (add function)
- Test: `tests/test_claude_runner.py`, `tests/test_workflow_regressions.py`, `tests/test_git_host.py`

**Interfaces:**
- Produces: `WorkflowConfig.headless_timeout: int` (seconds, default **3600**) and `verify_timeout: int` (default **1800**), both > 0. Interactive runs get **no** timeout.
- On `subprocess.TimeoutExpired`: headless → `ClaudeResult(returncode=124, stderr="timed out after Ns")`; verify → that command is `FAIL (timeout)`.
- Produces: `git_host.changed_paths(worktree: Path) -> list[str]` from `git status --porcelain`. The verify message becomes: `Verification changed the worktree diff: <paths>. Add generated files to .gitignore.`

- [ ] **Step 1: Write failing tests** — `test_headless_timeout_returns_124`, `test_verify_command_timeout_is_failure`, `test_verify_diff_change_lists_paths`, `test_changed_paths_lists_untracked`.
- [ ] **Step 2: Run, expect FAIL** — `$PYTEST`
- [ ] **Step 3: Implement**
- [ ] **Step 4: Run, expect PASS** — `$PYTEST`
- [ ] **Step 5: Commit** — `feat(workflow): add timeouts and list files changed by verify`

---

### Task 12: Token refresh, proxy log, one credentials file

**Why:** the proxy only allows `api.anthropic.com`. Claude Code 2.1.322 refreshes tokens at **`https://platform.claude.com/v1/oauth/token`** (found in the binary), so an expired token can't be refreshed in Q&A, Implement, Review or Retro (H6). Also, each ticket keeps its own copy of the credentials, so the sandbox copy and the host copy refresh separately.

**Files:**
- Modify: `claude_workflow/net_proxy.py:12, 48-68, 142-149`
- Modify: `claude_workflow/claude_runner.py:54-60`
- Modify: `claude_workflow/sandbox.py:128-151` and the bwrap binds
- Test: `tests/test_net_proxy.py`, `tests/test_sandbox.py`

**Interfaces:**
- Changes: `DEFAULT_ALLOWED_HOSTS = ("api.anthropic.com", "platform.claude.com")`
- Changes: `ConnectAllowlistProxy(..., log_path: Path | None = None)` appends one line per request: `ALLOW host:port` / `DENY host:port` / `REJECT <method>`. The runner passes `<state_dir>/proxy.log`.

- [ ] **Step 1: Investigate how Claude writes `.credentials.json`.** Run `stat -c %i ~/.claude/.credentials.json`, log in again (`claude` → `/login`), and run `stat` again.
  - **Same inode** (written in place) → **bind-mount the host file read-write** into the sandbox, and stop copying. One file, no drift.
  - **New inode** (atomic rename; that fails on a bind mount) → keep the copy, but **re-copy from the host when the host file is newer**, at every run start.
  - Write the result down in this task before going on.
- [ ] **Step 2: Write failing tests** — `test_proxy_allows_platform_claude_com_by_default`, `test_proxy_logs_allow_and_deny(tmp_path)`, plus one test for the credentials option chosen in step 1.
- [ ] **Step 3: Run, expect FAIL** — `$PYTEST tests/test_net_proxy.py tests/test_sandbox.py`
- [ ] **Step 4: Implement**
- [ ] **Step 5: Run, expect PASS** — `$PYTEST`
- [ ] **Step 6: Commit** — `fix(workflow): allow token refresh host and log proxy decisions`

---

### Task 13: Finalize commit without hooks (D2)

**Why:** `git commit` on the host runs the repo's hooks. A failing hook stops Finalize, and a formatting hook breaks the "diff unchanged" check (M4).

**Files:**
- Modify: `claude_workflow/git_host.py:114-120`, `claude_workflow/pipeline.py:108`
- Modify: `claude_workflow/config.py` (`commit_no_verify: bool`, default **true**)
- Test: `tests/test_git_host.py`

**Interfaces:**
- Changes: `commit_stage(worktree_path: Path, message: str, *, no_verify: bool = False) -> bool` → adds `--no-verify`.

- [ ] **Step 1: Write failing test** — `test_commit_no_verify_skips_failing_hook`: a repo with `.git/hooks/pre-commit` that runs `exit 1`. `no_verify=True` → returns True. `no_verify=False` → raises `GitError`.
- [ ] **Step 2: Run, expect FAIL** — `$PYTEST tests/test_git_host.py`
- [ ] **Step 3: Implement**
- [ ] **Step 4: Run, expect PASS** — `$PYTEST`
- [ ] **Step 5: Commit** — `feat(workflow): optional --no-verify for final commit`

---

### Task 14: Nix cleanup, debug tool, docs

**Why:** unused and duplicate files (L6). The debug tool and docs 01–05 must match the new code.

**Files:**
- Delete: `roles/ai/configuration/scripts/claude-workflow.sh`
- Modify: `roles/ai/ai.nix:52-56` — remove the `xdg.configFile."claude-workflow/skills"` link (the wrapper's `CLAUDE_WORKFLOW_SKILLS` always wins)
- Modify: `roles/ai/configuration/workflows/workflow/tools/sandbox_shell.py` — new `build_bwrap_command` arguments, `--interactive` flag, uses `ensure_ticket_worktree` for repo stages
- Modify: `roles/ai/docs/01-…05-*.md`; mark fixed items in `06-bugs.md`

- [ ] **Step 1:** apply the changes above.
- [ ] **Step 2: Lint and type check**

```sh
nix shell nixpkgs#ruff nixpkgs#pyright -c sh -c 'ruff check . && pyright'
```

Expected: no errors.

- [ ] **Step 3: Full tests** — `$PYTEST` → all pass.
- [ ] **Step 4: Nix build** — `nix build .#homeConfigurations."joey@work".activationPackage` from the dotfiles root, or your usual home-manager build. Expected: it succeeds, and the tests run during the build.
- [ ] **Step 5: Manual sandbox check** — `sandbox_shell.py` for each stage: `env` shows no tokens, `vendor/` is visible in Implement, and `curl https://platform.claude.com` doesn't give 403 in Q&A.
- [ ] **Step 6: Commit** — `chore(ai): cleanup, update sandbox_shell and docs`

---

### Task 15: Configurable Atlassian MCP check (D1)

**Why:** the Intake pre-check only accepts a top-level `mcpServers.atlassian` (M7). **The details depend on D1.**

**Default (D1 = keep `atlassian`):**

- New config key `stages.intake.mcp_server` (default `"atlassian"`).
- The pre-check looks for that name under the top-level `mcpServers` **and** under `projects.*.mcpServers` in `.claude.json`.
- Error message: `No MCP server named '<name>' found in ~/.claude.json; set stages.intake.mcp_server or mcp_config.`

**If you use the claude.ai connector instead:** remove the pre-check (connectors are not in `.claude.json`). Set `allowed_tools` to `mcp__claude_ai_Atlassian_Rovo__*`, and rely on the "fresh `01-ticket.md`" check to catch failures.

- [ ] **Step 1: Write failing tests** — `test_intake_accepts_configured_server_name`, `test_intake_finds_project_scoped_server`.
- [ ] **Step 2: Run, expect FAIL** — `$PYTEST`
- [ ] **Step 3: Implement**
- [ ] **Step 4: Run, expect PASS** — `$PYTEST`
- [ ] **Step 5: Commit** — `feat(workflow): configurable atlassian mcp server name`
