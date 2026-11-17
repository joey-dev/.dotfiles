# Jira-to-Branch Claude Workflow — Design Doc

> **Status:** Draft for approval
> **Target OS:** NixOS (via `roles/ai/` in `~/.dotfiles`)
> **Primary Tool:** Claude Code CLI (`claude`) + `bwrap` (bubblewrap)

---

## 1. Intent & Why

Turn a **Jira ticket ID** into a **working, clean local git branch** in a 12-year-old, 200k+ LOC mono-repo—without sacrificing code quality, context hygiene, or safety.

- **Phase 1 (Now):** Run **step-by-step** with approval gates between stages so you can inspect outputs and fine-tune custom skills.
- **Phase 2 (Later):** Run **multiple tickets in parallel** using isolated `git worktree`s, pausing only when human input is needed.

---

## 2. Goals, Non-Goals & Anti-Goals

### Goals
- Produce code that **solves the ticket**, looks **written by a senior developer**, and passes peer review with minimal comments.
- Enforce **least-privilege sandboxing** per stage via `bwrap` (read-only repo for research/planning/review; `.git` hidden from Claude).
- Support **re-running any single stage** (`--from-stage <name>`) with updated skills on saved inputs.
- Capture **clarifying questions**, **human review feedback**, and **knowledge base updates** so the system improves over time.

### Non-Goals
- **No automatic `git push` or PR creation** — the host stops at a clean local branch.
- **No parallel Docker Compose stacks** in v1 — integration/API tests share ports and stay serialized or in CI.
- **No MR-comment review pipeline in v1** — handling GitLab/GitHub MR comments will be a separate follow-up pipeline that reuses Stages 5–7.

### Anti-Goals (Failure Modes to Avoid)
- Unbounded review loops that burn tokens bike-shedding.
- Uncurated KB growth that feeds stale legacy assumptions into future runs.
- Giant, untyped scripts that are hard to read or extend.

---

## 3. Approaches Considered

| Approach | Summary | Trade-off |
|---|---|---|
| **A. Bash + `bwrap` + Stage Files** | `claude-workflow.sh` calling per-stage `.sh` scripts. | Fast to start, zero deps; gets messy for state/parallel queues. |
| **B. Python + `bwrap` + Stage Files (Picked)** | Typed Python CLI (`dataclass` state, small stage modules) wrapping `bwrap` + `claude`. | Slightly more boilerplate; much cleaner state, loop caps, and parallel workers. |
| **C. Claude Agent SDK / `stream-json`** | Programmatic SDK loop. | Harder to drop into interactive Q&A or inspect/retry intermediate files. |

---

## 4. Pipeline Architecture

Each ticket gets a dedicated state directory (placeholder: `~/.local/state/claude-workflow/<TICKET>/`) and a `git worktree` (created before implementation). All paths are centralized in `config.py` and will be set to your real NixOS paths before scaffolding.

```
[1. Intake] -> [2. Explore] -> [3. Interactive Q&A] -> [4. Plan (+ max 2 review passes)]
                                                               |
[8. Human Check & Retro] <- [7. Automated Code Review] <- [6. Verify] <- [5. Implement]
```

### Stage Breakdown

| # | Stage | Mode | Repo Mount | Network / MCP | Primary Output |
|---|---|---|---|---|---|
| 1 | **Intake** | Headless | None | Atlassian MCP | `01-ticket.md` (summary, comments, linked issues) |
| 2 | **Explore** | Headless | Read-only (`.git` hidden) | Read-only docs (`WebFetch`/Context7) | `02-findings.md` (relevant files, legacy quirks, gaps) |
| 3 | **Q&A** | **Interactive** | Read-only (`.git` hidden) | None | `03-qa.md` (batched questions + answers, saved incrementally) |
| 4 | **Plan** | Headless | Read-only (`.git` hidden) | Read-only docs (`WebFetch`/Context7) | `04-plan.md` (steps, test plan; max 2 reviewer passes) |
| 5 | **Implement** | Headless | **Read-write worktree** (`.git` hidden) | None (`--unshare-net`) | Code changes + host commits per step |
| 6 | **Verify** | Host / `bwrap` | Worktree | Optional (Docker) | `06-verify.md` (linters + unit tests via `flake.nix`) |
| 7 | **Code Review** | Headless | Read-only + `diff.patch` | None (`--unshare-net`) | `07-review.md` (2 focused lenses: Correctness + Conventions) |
| 8 | **Human Check & Retro** | **Interactive / Host** | Read-only KB + `feedback.md` | None | Your local branch check + proposed diff to skills / KB |

### Key Mechanics

- **Whole-pipeline crash-safety:** `state.json` tracks `last_completed_stage`, `current_stage`, and `session_ids`. Re-running `workflow <TICKET>` automatically resumes from `current_stage` (restarting the interrupted stage cleanly, or using `--resume` for Stage 3 Q&A).
- **Escalation questions after Stage 3:** Stage 3 batches most questions up front. If Stage 4 (**Plan**) or Stage 5 (**Implement**) hits a genuine unknown, it writes `blocked-questions.md` and exits cleanly instead of guessing; the orchestrator runs a short Interactive Q&A turn, appends answers to `03-qa.md`, and retries the stage.
- **Read-only doc lookups:** Stages 2 & 4 allow read-only documentation lookups (e.g., `WebFetch` / Context7 MCP, with `curl`/`wget` disallowed) so framework docs stay current without giving write access to websites. Stages 5 & 7 run with `--unshare-net`.
- **Approval gates:** By default (`--step` mode), the script pauses after each stage and prompts `[c]ontinue / [r]etry stage / [a]bort`. Passing `--auto` skips gates except **Stage 3 (Q&A)** and **Stage 8 (Human Check & Retro)**.
- **Git safety:** `.git` is hidden inside `bwrap`. The **host Python orchestrator** runs `git worktree add`, `git diff`, and `git commit` between stages.
- **Stage-isolated skills:** Each stage mounts only `skills/shared/` + `skills/<stage>/` read-only into the sandbox.
- **Personal Knowledge Base:** Stored outside all repos (placeholder: `~/notes/work-kb/`), mounted **read-only** in Stages 2, 3, 4, and 7. Updated only when you approve Stage 8's diff.
- **Model & thinking config:** Defined in a typed `StageConfig` mapping (e.g., Sonnet for Intake/Implement, Opus or high-thinking Sonnet for Explore/Plan/Review), overridable per ticket complexity.

---

## 5. Python Code Structure & Maintainability

To keep the codebase clean and easy to read:

- **Strict typing:** `from __future__ import annotations`, full type annotations on all functions, `dataclass` / `Enum` models, checked with `pyright` or `mypy` + `ruff`.
- **Small, single-purpose modules:**
  - `cli.py` — argument parsing (`ticket`, `--from-stage`, `--step` / `--auto`).
  - `config.py` — typed `StageConfig`, paths, model/thinking defaults.
  - `sandbox.py` — `bwrap` command builder (mounts, env, network isolation).
  - `claude_runner.py` — invokes `claude` (headless or interactive/resume).
  - `git_host.py` — host-side `worktree`, `diff.patch`, and `commit` helpers.
  - `stages/` — one small file per stage (`intake.py`, `explore.py`, `qa.py`, etc.).
- **Docstrings:** Concise docstring on every module, class, and public function.

---

## 6. Left to the Builder (Next Steps)

1. Confirm exact **NixOS paths** (mono-repo path, worktree base dir, Personal KB path, `flake.nix` test/lint commands).
2. Scaffold the Python package in `roles/ai/` and wire it into `ai.nix`.
3. Write and test the **first 2 custom skills** (`intake` and `explore`) on a real Jira ticket before building later stages.
