# Jira-to-Branch Workflow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (chosen by user) to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. **Note:** Do NOT run `git commit`, `git push`, or `git checkout`/`switch` — the user handles git commits manually.

**Goal:** Build a typed, modular Python + `bwrap` orchestrator (`claude-workflow`) in `roles/ai/configuration/workflows/workflow/` that runs an 8-stage, crash-safe Jira-to-branch pipeline with stage-isolated custom skills and NixOS integration.

**Architecture:** A small Python 3.12+ package (zero third-party runtime dependencies) manages per-ticket state (`state.json` + stage `.md` artifacts) and host-side `git worktree` operations. Each stage runs `claude` inside a least-privilege `bwrap` sandbox (hiding `.git`, mounting only that stage's skills and a read-only Personal KB), with `--step` approval gates, `--from-stage` retries, and `blocked-questions.md` escalation back to interactive Q&A.

**Tech Stack:** Python 3.12+ (`dataclasses`, `enum`, `pathlib`, `subprocess`, `json`, `argparse`), `pytest`, `pyright` / `mypy`, `ruff`, `bubblewrap` (`bwrap`), `git`, NixOS (`home-manager` in `roles/ai/ai.nix`).

**Spec:** [02-design.md](./02-design.md)

---

## Global Constraints

- **Target OS:** NixOS only (`roles/ai/` in `~/.dotfiles`).
- **Maintainability:** Strict type annotations (`from __future__ import annotations`), `dataclass`/`Enum` models, small single-purpose files, concise docstrings on every module, class, and public function.
- **Zero runtime PyPI deps:** Standard library only at runtime so Nix packaging stays trivial.
- **Git safety:** `.git` is always hidden inside `bwrap`; only the host Python process runs `git` commands; **never** auto-push.
- **Crash-safety:** Persist `state.json` atomically (`tmp` + `os.replace`) before and after every stage.
- **Escalation & caps:** Plan review loops capped at 2; `Plan` and `Implement` may emit `blocked-questions.md` to trigger a short interactive Q&A turn instead of guessing.
- **No hardcoded machine paths:** All user/repo/KB paths load from `config.json` / CLI flags / defaults in `config.py`.

## Review Focus

1. **Worktree `.git` is a file, not a directory:** `bwrap --tmpfs` fails on a file; `sandbox.py` must detect `is_file()` vs `is_dir()` and use `--ro-bind /dev/null <path>` for a `.git` file.
2. **Crash mid-stage (`Ctrl+C` or killed process):** `state.json` must record `current_stage` *before* launching `claude`, so re-running `claude-workflow <TICKET>` resumes that exact stage cleanly (and uses `--resume` for Stage 3 Q&A).
3. **Partial/corrupt `state.json` write:** Always write to `state.json.tmp` and `os.replace()` so an interrupt never corrupts state.
4. **Escalation loop infinite cycle:** Cap `blocked-questions.md` escalations per stage (e.g. max 3) so a confused agent cannot loop forever.
5. **Empty diff on Implement/Commit:** `git_host.commit_stage()` must check `git status --porcelain` first and return `False` cleanly instead of failing on `git commit` with nothing staged.

---

## File Structure

```text
roles/ai/
├── ai.nix                                      # Updated to package ./configuration/workflows/workflow as claude-workflow
├── planning/
│   ├── 00-jira-workflow.md
│   ├── 01-critical-review.md
│   ├── 02-design.md
│   └── 03-implementation-plan.md               # This file
└── configuration/workflows/workflow/
    ├── pyproject.toml                          # Package metadata, pytest/pyright/ruff config
    ├── claude_workflow/
    │   ├── __init__.py
    │   ├── config.py               # StageName, RepoAccess, StageConfig, WorkflowConfig
    │   ├── state.py                # TicketState, atomic load/save, resume logic
    │   ├── sandbox.py              # bwrap command builder
    │   ├── git_host.py             # Host-side worktree, diff, commit helpers
    │   ├── claude_runner.py        # Claude CLI invocation (headless & interactive)
    │   ├── pipeline.py             # Stage runner, gates, escalation, retry loop
    │   ├── cli.py                  # CLI entrypoint
    │   └── stages/
    │       ├── __init__.py
    │       ├── base.py             # StageResult, StageProtocol
    │       ├── intake.py           # Stage 1: Atlassian MCP -> 01-ticket.md
    │       ├── explore.py          # Stage 2: RO repo + docs -> 02-findings.md
    │       ├── qa.py               # Stage 3: Interactive Q&A -> 03-qa.md
    │       ├── plan.py             # Stage 4: Plan + max 2 review passes -> 04-plan.md
    │       ├── implement.py        # Stage 5: RW worktree -> code changes
    │       ├── verify.py           # Stage 6: flake.nix linters + unit tests -> 06-verify.md
    │       ├── review.py           # Stage 7: RO 2-lens code review -> 07-review.md
    │       └── retro.py            # Stage 8: Human check + KB/skill diff proposal
    ├── skills/                     # Starter stage-isolated skills
    │   ├── shared/SKILL.md
    │   ├── intake/SKILL.md
    │   ├── explore/SKILL.md
    │   ├── qa/SKILL.md
    │   ├── plan/SKILL.md
    │   ├── implement/SKILL.md
    │   ├── review/SKILL.md
    │   └── retro/SKILL.md
    └── tests/
        ├── test_config.py
        ├── test_state.py
        ├── test_sandbox.py
        ├── test_git_host.py
        ├── test_claude_runner.py
        └── test_pipeline.py
```

---

### Task 1: Project Scaffold, Config & Atomic State (`config.py`, `state.py`)

**Files:**
- Create: `roles/ai/configuration/workflows/workflow/pyproject.toml`
- Create: `roles/ai/configuration/workflows/workflow/claude_workflow/__init__.py`
- Create: `roles/ai/configuration/workflows/workflow/claude_workflow/config.py`
- Create: `roles/ai/configuration/workflows/workflow/claude_workflow/state.py`
- Test: `roles/ai/configuration/workflows/workflow/tests/test_config.py`
- Test: `roles/ai/configuration/workflows/workflow/tests/test_state.py`

**Interfaces:**
- Produces:
  - `StageName(str, Enum)`: `INTAKE`, `EXPLORE`, `QA`, `PLAN`, `IMPLEMENT`, `VERIFY`, `REVIEW`, `RETRO`
  - `RepoAccess(str, Enum)`: `NONE`, `RO`, `RW`
  - `StageConfig` (dataclass): `name: StageName`, `model: str`, `thinking: str`, `repo_access: RepoAccess`, `allow_network: bool`, `mcp_config: Path | None`, `allowed_tools: tuple[str, ...]`
  - `WorkflowConfig` (dataclass): `repo_path: Path`, `worktree_base: Path`, `state_base: Path`, `kb_path: Path`, `skills_base: Path`, `verify_commands: tuple[str, ...]`, `max_plan_reviews: int`, `max_escalations: int`, `stages: dict[StageName, StageConfig]`
  - `load_config(config_path: Path | None) -> WorkflowConfig`
  - `TicketState` (dataclass): `ticket_id: str`, `current_stage: StageName | None`, `completed_stages: list[StageName]`, `session_ids: dict[str, str]`, `worktree_path: Path | None`, `branch_name: str`
  - `load_state(state_dir: Path, ticket_id: str) -> TicketState`
  - `save_state(state_dir: Path, state: TicketState) -> None`
  - `next_stage_to_run(state: TicketState, from_stage: StageName | None) -> StageName | None`

- [ ] **Step 1: Create `pyproject.toml` and `__init__.py`**
  Configure Python >= 3.12, `pytest`, `pyright` (strict mode), and `ruff` in `roles/ai/configuration/workflows/workflow/pyproject.toml`.

- [ ] **Step 2: Write failing tests in `tests/test_config.py` and `tests/test_state.py`**
  Test:
  - `test_load_config_defaults_and_json_override(tmp_path: Path)`: overrides `repo_path`, `kb_path`, and a stage's `model` from JSON while keeping other defaults.
  - `test_save_and_load_state_atomic(tmp_path: Path)`: round-trips `TicketState` and leaves no `.tmp` file behind.
  - `test_next_stage_resumes_interrupted_current_stage()`: if `current_stage == StageName.PLAN` and `completed_stages == [INTAKE, EXPLORE, QA]`, returns `PLAN`.
  - `test_next_stage_with_from_stage_override()`: `--from-stage explore` returns `EXPLORE` regardless of `completed_stages`.

- [ ] **Step 3: Run tests to verify they fail**
  Run: `pytest roles/ai/configuration/workflows/workflow/tests/test_config.py roles/ai/configuration/workflows/workflow/tests/test_state.py -v`
  Expected: FAIL (`ModuleNotFoundError`).

- [ ] **Step 4: Implement `config.py` and `state.py`**
  - Define default stage configs in `config.py` matching [02-design.md](./02-design.md) (e.g., `INTAKE` = `NONE` + Atlassian MCP; `EXPLORE`/`PLAN` = `RO` + network for read-only docs; `QA`/`REVIEW` = `RO` + offline; `IMPLEMENT` = `RW` + offline).
  - Implement atomic `save_state()` using `state.json.tmp` + `os.replace()`.

- [ ] **Step 5: Run tests + type check**
  Run: `pytest roles/ai/configuration/workflows/workflow/tests/test_config.py roles/ai/configuration/workflows/workflow/tests/test_state.py -v`
  Expected: PASS.

---

### Task 2: `bwrap` Sandbox Builder (`sandbox.py`)

**Files:**
- Create: `roles/ai/configuration/workflows/workflow/claude_workflow/sandbox.py`
- Test: `roles/ai/configuration/workflows/workflow/tests/test_sandbox.py`

**Interfaces:**
- Consumes: `StageConfig`, `WorkflowConfig` from `config.py`
- Produces:
  - `SandboxSpec` (dataclass): `repo_dir: Path | None`, `repo_access: RepoAccess`, `state_dir: Path`, `skills_dirs: tuple[Path, ...]`, `kb_dir: Path | None`, `allow_network: bool`, `workdir: Path`
  - `build_bwrap_command(spec: SandboxSpec, inner_cmd: Sequence[str]) -> list[str]`

- [ ] **Step 1: Write failing tests in `tests/test_sandbox.py`**
  Test:
  - `test_bwrap_ro_repo_and_unshare_net(tmp_path: Path)`: asserts `--ro-bind` for repo, `--unshare-net` present when `allow_network=False`, `--bind` for `state_dir`.
  - `test_bwrap_hides_git_directory(tmp_path: Path)`: when `repo/.git` is a directory, asserts `--tmpfs <repo>/.git` is in args.
  - `test_bwrap_hides_git_worktree_file(tmp_path: Path)`: when `worktree/.git` is a regular file, asserts `--ro-bind /dev/null <worktree>/.git` is in args (never `--tmpfs`).
  - `test_bwrap_mounts_only_stage_skills_and_ro_kb(tmp_path: Path)`: asserts `--ro-bind` for `kb_dir` and each skill dir.

- [ ] **Step 2: Run tests to verify they fail**
  Run: `pytest roles/ai/configuration/workflows/workflow/tests/test_sandbox.py -v`
  Expected: FAIL.

- [ ] **Step 3: Implement `sandbox.py`**
  Build the `bwrap` argument list cleanly: `--die-with-parent`, `--new-session`, `--ro-bind` for NixOS system paths (`/nix/store`, `/etc`, `/usr`, `/bin` if present), `--dev /dev`, `--proc /proc`, `--tmpfs /tmp`, repo/KB/skills/state mounts, `.git` masking, and conditional `--unshare-net`.

- [ ] **Step 4: Run tests to verify they pass**
  Run: `pytest roles/ai/configuration/workflows/workflow/tests/test_sandbox.py -v`
  Expected: PASS.

---

### Task 3: Host Git Helpers (`git_host.py`)

**Files:**
- Create: `roles/ai/configuration/workflows/workflow/claude_workflow/git_host.py`
- Test: `roles/ai/configuration/workflows/workflow/tests/test_git_host.py`

**Interfaces:**
- Produces:
  - `GitError(RuntimeError)`
  - `ensure_worktree(repo_path: Path, worktree_path: Path, branch_name: str, base_ref: str = "HEAD") -> Path`
  - `is_dirty(worktree_path: Path) -> bool`
  - `capture_diff(worktree_path: Path, base_ref: str = "HEAD") -> str`
  - `commit_stage(worktree_path: Path, message: str) -> bool`

- [ ] **Step 1: Write failing tests in `tests/test_git_host.py`**
  Test (using a real temp git repo in `tmp_path`):
  - `test_ensure_worktree_creates_branch_and_is_idempotent(tmp_path: Path)`
  - `test_capture_diff_includes_untracked_and_modified(tmp_path: Path)`
  - `test_commit_stage_returns_false_when_clean_and_true_when_dirty(tmp_path: Path)`

- [ ] **Step 2: Run tests to verify they fail**
  Run: `pytest roles/ai/configuration/workflows/workflow/tests/test_git_host.py -v`
  Expected: FAIL.

- [ ] **Step 3: Implement `git_host.py`**
  Use `subprocess.run(..., check=True, capture_output=True, text=True)` with explicit error wrapping into `GitError`. Never implement `push`, `fetch`, or `pull`.

- [ ] **Step 4: Run tests to verify they pass**
  Run: `pytest roles/ai/configuration/workflows/workflow/tests/test_git_host.py -v`
  Expected: PASS.

---

### Task 4: Claude CLI Runner (`claude_runner.py`)

**Files:**
- Create: `roles/ai/configuration/workflows/workflow/claude_workflow/claude_runner.py`
- Test: `roles/ai/configuration/workflows/workflow/tests/test_claude_runner.py`

**Interfaces:**
- Consumes: `StageConfig` (`config.py`), `build_bwrap_command`, `SandboxSpec` (`sandbox.py`)
- Produces:
  - `ClaudeResult` (dataclass): `returncode: int`, `stdout: str`, `stderr: str`, `session_id: str | None`
  - `run_claude_headless(stage: StageConfig, sandbox: SandboxSpec, prompt: str, session_id: str | None = None) -> ClaudeResult`
  - `run_claude_interactive(stage: StageConfig, sandbox: SandboxSpec, prompt: str, session_id: str, resume: bool = False) -> int`

- [ ] **Step 1: Write failing tests in `tests/test_claude_runner.py`**
  Test (monkeypatching `subprocess.run`):
  - `test_headless_builds_expected_claude_flags(tmp_path: Path)`: verifies `-p`, `--model`, `--allowedTools`, and `--mcp-config` when set.
  - `test_interactive_uses_session_id_or_resume(tmp_path: Path)`: verifies `--session-id <uuid>` on fresh run and `--resume <uuid>` when `resume=True`.

- [ ] **Step 2: Run tests to verify they fail**
  Run: `pytest roles/ai/configuration/workflows/workflow/tests/test_claude_runner.py -v`
  Expected: FAIL.

- [ ] **Step 3: Implement `claude_runner.py`**
  Wrap `claude` invocation with `build_bwrap_command()`. Headless captures output; interactive inherits terminal stdio so the user can chat live.

- [ ] **Step 4: Run tests to verify they pass**
  Run: `pytest roles/ai/configuration/workflows/workflow/tests/test_claude_runner.py -v`
  Expected: PASS.

---

### Task 5: Stage Implementations & Pipeline Orchestrator (`stages/*.py`, `pipeline.py`)

**Files:**
- Create: `roles/ai/configuration/workflows/workflow/claude_workflow/stages/__init__.py`
- Create: `roles/ai/configuration/workflows/workflow/claude_workflow/stages/base.py`
- Create: `roles/ai/configuration/workflows/workflow/claude_workflow/stages/intake.py`
- Create: `roles/ai/configuration/workflows/workflow/claude_workflow/stages/explore.py`
- Create: `roles/ai/configuration/workflows/workflow/claude_workflow/stages/qa.py`
- Create: `roles/ai/configuration/workflows/workflow/claude_workflow/stages/plan.py`
- Create: `roles/ai/configuration/workflows/workflow/claude_workflow/stages/implement.py`
- Create: `roles/ai/configuration/workflows/workflow/claude_workflow/stages/verify.py`
- Create: `roles/ai/configuration/workflows/workflow/claude_workflow/stages/review.py`
- Create: `roles/ai/configuration/workflows/workflow/claude_workflow/stages/retro.py`
- Create: `roles/ai/configuration/workflows/workflow/claude_workflow/pipeline.py`
- Test: `roles/ai/configuration/workflows/workflow/tests/test_pipeline.py`

**Interfaces:**
- Consumes: `config.py`, `state.py`, `sandbox.py`, `git_host.py`, `claude_runner.py`
- Produces:
  - `StageOutcome(str, Enum)`: `DONE`, `BLOCKED_QUESTIONS`, `FAILED`
  - `StageContext` (dataclass): `ticket_id: str`, `config: WorkflowConfig`, `state: TicketState`, `state_dir: Path`
  - `StageResult` (dataclass): `outcome: StageOutcome`, `artifact_path: Path | None`, `message: str`
  - `run_pipeline(ticket_id: str, config: WorkflowConfig, from_stage: StageName | None = None, auto: bool = False) -> int`

- [ ] **Step 1: Write failing tests in `tests/test_pipeline.py`**
  Test (with fake runner + fake prompt input):
  - `test_pipeline_runs_all_stages_and_persists_state(tmp_path: Path)`
  - `test_pipeline_resumes_from_interrupted_stage(tmp_path: Path)`
  - `test_pipeline_handles_blocked_questions_escalation_and_caps_retries(tmp_path: Path)`
  - `test_plan_stage_caps_review_loop_at_max_plan_reviews(tmp_path: Path)`
  - `test_step_gate_allows_retry_continue_and_abort(tmp_path: Path)`

- [ ] **Step 2: Run tests to verify they fail**
  Run: `pytest roles/ai/configuration/workflows/workflow/tests/test_pipeline.py -v`
  Expected: FAIL.

- [ ] **Step 3: Implement `stages/base.py`, the 8 stage modules, and `pipeline.py`**
  - Each stage module stays small (~40–80 lines), builds its prompt from prior artifacts, invokes `claude_runner` (or `verify_commands` in `verify.py`), and checks for `blocked-questions.md`.
  - `plan.py` runs draft -> reviewer pass (capped at `config.max_plan_reviews`).
  - `review.py` runs 2 focused read-only lenses (`correctness` and `conventions`) on `diff.patch` and writes `07-review.md`.
  - `pipeline.py` handles `state.json` checkpoints, `--step` approval gates, `notify-send` alerts when human input is needed, and escalation Q&A.

- [ ] **Step 4: Run tests to verify they pass**
  Run: `pytest roles/ai/configuration/workflows/workflow/tests/test_pipeline.py -v`
  Expected: PASS.

---

### Task 6: CLI Entrypoint, Starter Custom Skills & NixOS Integration (`cli.py`, `skills/`, `ai.nix`)

**Files:**
- Create: `roles/ai/configuration/workflows/workflow/claude_workflow/cli.py`
- Create: `roles/ai/configuration/workflows/workflow/skills/shared/SKILL.md`
- Create: `roles/ai/configuration/workflows/workflow/skills/intake/SKILL.md`
- Create: `roles/ai/configuration/workflows/workflow/skills/explore/SKILL.md`
- Create: `roles/ai/configuration/workflows/workflow/skills/qa/SKILL.md`
- Create: `roles/ai/configuration/workflows/workflow/skills/plan/SKILL.md`
- Create: `roles/ai/configuration/workflows/workflow/skills/implement/SKILL.md`
- Create: `roles/ai/configuration/workflows/workflow/skills/review/SKILL.md`
- Create: `roles/ai/configuration/workflows/workflow/skills/retro/SKILL.md`
- Modify: `roles/ai/ai.nix:1-31`

**Interfaces:**
- Consumes: `load_config`, `StageName`, `run_pipeline`
- Produces: CLI command `claude-workflow <TICKET> [--from-stage <stage>] [--auto] [--config <path>]`

- [ ] **Step 1: Implement `cli.py` and starter `skills/*/SKILL.md` files**
  - Starter skills encode the core rules (batch questions in `qa`, emit `blocked-questions.md` if truly stuck in `plan`/`implement`, adversarial "someone else wrote this" framing in `review`).

- [ ] **Step 2: Update `roles/ai/ai.nix`**
  - Package `./configuration/workflows/workflow` via `pkgs.python3Packages.buildPythonApplication` (with `pyproject = true`, `pytestCheckHook`, and `makeWrapper` adding `bubblewrap`, `git`, `libnotify`, `claude-code` to `PATH`), replacing the empty `claude-workflow.sh` wrapper.

- [ ] **Step 3: Run full test suite + type check + lint**
  Run: `pytest roles/ai/configuration/workflows/workflow/tests -v`
  Run: `pyright roles/ai/workflow` (if available) and `ruff check roles/ai/workflow`
  Expected: All tests pass, zero type errors, zero lint errors.
