# 2. What each step does

This document explains **each stage**: what it reads, what it writes, what it is **allowed** to do, and how it ends.

All Python files mentioned live in `roles/ai/configuration/workflows/workflow/claude_workflow/`. Settings come from `configuration/workflows/config/global.config.json` (and the repo file).

---

## 2.0 Things that are the same for every stage

### Where files go

- Every ticket gets its own **state directory**: `~/.local/state/claude-workflow/<TICKET>/`.
- Inside the sandbox this directory is visible as **`~/notes/`**. All stage artifacts (`01-ticket.md`, …) are written there.
- `state.json` and `.lock` are **hidden** from Claude (replaced by `/dev/null`).

### The ticket worktree

- Created at **Explore** (`ensure_ticket_worktree`, `stages/base.py:57`).
- Branch = ticket in lower case (`proj-123`). Path = `~/.local/state/claude-workflow/worktrees/<TICKET>`.
- Base commit = `HEAD` of your main checkout **the first time**. It never moves after that.
- Uncommitted changes in your main checkout are **not** included. You get a warning.
- Every stage that needs code (Explore, Q&A, Plan, Implement, Verify, Review, escalation Q&A) uses this worktree.

### The sandbox (bubblewrap)

Every Claude call runs inside **`bwrap`** (`sandbox.py:219`). Claude sees:

- a **fake `$HOME`** (`<state dir>/home`) with your Claude login;
- a **generated `settings.json`**: your settings **without hooks**, read-only;
- your personal **`~/.claude/CLAUDE.md`**, read-only;
- the **worktree** at `~/<TICKET>` (read-only or read-write, per stage), with **`.git` hidden**;
- **`vendor/` and `node_modules/`** from your main checkout, read-only, when the lockfiles match (see 2.0.1);
- the **knowledge base** (`kb_path`) read-only at `~/kb`, if the stage gets it and the folder exists;
- a **clean environment**: only a short allowlist of your variables, plus the flake's dev shell variables, captured with `nix develop --ignore-environment` (`env.py`).

### 2.0.1 Shared dependencies

Code: `deps.py`. Per entry in `shared_dependencies` (default: `vendor` + `composer.lock`, `node_modules` + `package-lock.json`):

1. The worktree has its **own** non-empty folder → use it.
2. The main checkout has no such folder → skip.
3. The lockfile **differs** from the main checkout → stop with an error and tell you to install on the host.
4. Otherwise → mount the main checkout's folder **read-only** into the worktree.

### Skills

- The `shared` skill and the stage's own skill are sent as a **system prompt** (`--append-system-prompt`).
- Skills are **not** mounted as files, except for Retro (all skills at `~/skills`, read-only).

### Network

- **`allow_network: true`** → full internet.
- **`allow_network: false`** → no network, **except** `api.anthropic.com` and `platform.claude.com` (login refresh) on port 443, through a proxy.
- Every proxy decision is logged to `<state dir>/proxy.log` (`ALLOW`, `DENY`, `REJECT`).

### Login

- Your `~/.claude/.credentials.json` is copied **into** the sandbox when it's missing there, or when your host token expires later (`_copy_login_in` in `sandbox.py`).
- It's **never copied back**, so a compromised stage can't change your real login.
- Stages with MCP servers also get `~/.mcp-auth` copied in, the same safe one-way way.
- The copy never follows symlinks the sandbox may have planted.

### How a stage ends

| Outcome | Meaning | What happens next |
|---|---|---|
| **DONE** | Artifact written and fresh | Approval gate |
| **BLOCKED_QUESTIONS** | Plan/Implement wrote a non-empty `blocked-questions.md` | Escalation Q&A, then re-run |
| **NEEDS_FIX** | Verify check failed, or Review asked for changes | Fix choice (see doc 1, 1.3) |
| **FAILED** | Error, timeout, no fresh artifact, or no verdict | Program stops (exit 1) |

"**Fresh**" means the file exists, is not empty, and changed during this run.

### Timeouts

- Each headless Claude call: **`headless_timeout`** (default 3600 s). On timeout: FAILED.
- Each verify command: **`verify_timeout`** (default 1800 s). On timeout: that check fails.
- Interactive stages have **no** timeout.

---

## 2.1 Intake

**Goal:** fetch the Jira ticket and turn it into a clean summary.

| | |
|---|---|
| **Runs as** | Headless (`claude -p`) |
| **Model / effort** | sonnet / medium |
| **Repo access** | none |
| **Network** | full |
| **Tools** | `Read`, `Write`, `mcp__Atlassian-Rovo-MCP__*` |
| **Reads** | Jira, via the **`Atlassian-Rovo-MCP` server** from the repo's `.mcp.json` |
| **Writes** | `01-ticket.md` |
| **Code** | `stages/intake.py` |

- A stage that allows `mcp__*` tools gets the repo's **`.mcp.json`** (only those servers), unless `mcp_config` is set.
- The server runs `npx mcp-remote …`. Its Atlassian login (`~/.mcp-auth`) is **copied in, one way**: per file, when missing or newer on the host.
- If it fails, the message tells you what to check.

**Can:** read Jira, write in the state dir. **Cannot:** see the repo, ask you questions, escalate.

---

## 2.2 Explore

**Goal:** find the code that matters for this ticket.

| | |
|---|---|
| **Runs as** | Headless |
| **Model / effort** | opus / high |
| **Repo access** | read-only (**ticket worktree**, created here) |
| **Network** | full |
| **KB** | yes, read-only |
| **Tools** | `Read`, `Glob`, `Grep`, `Write`, `WebFetch` |
| **Reads** | `01-ticket.md`, worktree, KB |
| **Writes** | `02-findings.md` |
| **Code** | `stages/explore.py` |

---

## 2.3 Q&A

**Goal:** get your answers to open questions **before** planning.

| | |
|---|---|
| **Runs as** | **Interactive**, with a real terminal (resize and Ctrl-C work) |
| **Model / effort** | sonnet / medium |
| **Repo access** | read-only (worktree) |
| **Network** | Anthropic only |
| **KB** | yes, read-only |
| **Tools** | `Read`, `Glob`, `Grep`, `Write` |
| **Reads** | `01-ticket.md`, `02-findings.md` |
| **Writes** | `03-qa.md` |
| **Code** | `stages/qa.py` |

- You end the session yourself. Exit code 0 + fresh `03-qa.md` → **DONE**.
- **Ctrl-C** (exit 130) keeps the session, so the next run **resumes the same conversation**.
- **`--auto` does not skip this.**

---

## 2.4 Plan

**Goal:** write a concrete, **test-first** implementation plan, and let a reviewer check it.

| | |
|---|---|
| **Runs as** | Headless, several calls |
| **Model / effort** | opus / high |
| **Repo access** | read-only (worktree) |
| **Network** | full |
| **KB** | yes, read-only |
| **Tools** | `Read`, `Glob`, `Grep`, `Write`, `WebFetch` |
| **Reads** | `01-ticket.md`, `02-findings.md`, `03-qa.md` |
| **Writes** | `04-plan.md`, `04-plan-review.md`, maybe `blocked-questions.md` |
| **Code** | `stages/plan.py` |

1. **Draft:** writes `04-plan.md`. Each step names the test to write before its code.
2. **Review pass:** a new Claude call writes `04-plan-review.md`, starting with `APPROVED` or `CHANGES_REQUESTED`. Markdown around the word is fine, but extra words after it are not (`APPROVED WITH CHANGES` is no verdict).
3. **Revise:** if changes are requested, a new call rewrites the plan. Back to step 2.
4. Stops after `max_plan_reviews` (default **2**) review passes.

**Can escalate:** yes, from the draft, a revise, **or the reviewer**.

---

## 2.5 Implement

**Goal:** change the code according to the plan, **test-first**.

| | |
|---|---|
| **Runs as** | Headless |
| **Model / effort** | sonnet / high |
| **Repo access** | **read-write** on the ticket worktree |
| **Network** | Anthropic only |
| **KB** | no |
| **Tools** | `Read`, `Edit`, `Write`, `Glob`, `Grep`, `Bash` |
| **Dev shell** | the flake's environment, if `flake-path` is set |
| **Reads** | `04-plan.md`, `03-qa.md`, and the fix feedback file if set |
| **Writes** | code in the worktree, `05-implement.md`, maybe `blocked-questions.md` |
| **Code** | `stages/implement.py` |

- The prompt asks for **red-green**: write the test, see it fail, write the code until it passes.
- It shows the **command catalogue** (from the repo config's `commands`) and what Verify always runs (`verify`). For `sandbox` commands it also shows the line, so Claude can run that check itself (`_test_first_instruction`, `stages/implement.py`).
- In a fix round: *"Fix the problems listed in ~/notes/06-verify.md"* (or `07-review.md`).
- **No git** (`.git` is hidden) and **no network** except Anthropic.
- Implement does **not commit**.

---

## 2.6 Verify

**Goal:** run your linters and tests on the changed worktree.

| | |
|---|---|
| **Runs as** | **No Claude.** The host runs **named commands** from the repo config |
| **Repo access** | worktree, read-write mount (sandbox commands) |
| **Network** | **none** in the sandbox |
| **Dev shell** | the flake's environment, if `flake-path` is set |
| **Reads** | `tests.txt` (written by Plan / Implement) |
| **Writes** | `06-verify.md` |
| **Code** | `stages/verify.py`, `runners.py`, `docker_stack.py` |

**What runs:**

- First every entry of **`verify`** (trusted config; these get the Verify cache).
- Then every line of **`tests.txt`**: `<command> [key=value ...]`. Values are **checked on the host** against the parameter's `pattern` (no cache).
- Each command has a **`run-in`**:
  - **`sandbox`**: bwrap, no network;
  - **`host`**: the **base-commit copy** of the script runs on the host, after the guard;
  - **`container`**: `docker exec` into a running container.
- **`needs-compose-stack: true`** starts the compose stack from the worktree first (once per run).

**Steps:**

1. No `tests.txt` → **NEEDS_FIX** (write it).
2. Takes a snapshot of the diff, then runs every command.
3. The diff **changed** → FAILED, with the list of changed files.
4. Stores a **fingerprint of the diff** (`verified_diff`).
5. Any command failed or timed out → **NEEDS_FIX**.
6. Only a **host stop** (guard tripped, new symlink, preparing failed) → **NEEDS_HUMAN**. Otherwise → **DONE**.
7. A command with no changed files to check is **skipped**, not passed.

---

## 2.7 Review

**Goal:** an automated code review of the diff, like reviewing a colleague's MR.

| | |
|---|---|
| **Runs as** | Headless, 2 calls (one per lens) |
| **Model / effort** | opus / high |
| **Repo access** | worktree, read-only |
| **Network** | Anthropic only |
| **KB** | yes, read-only |
| **Reads** | `diff.patch`, `01-ticket.md`, `04-plan.md` |
| **Writes** | `diff.patch`, `07-review-correctness.md`, `07-review-conventions.md`, `07-review.md` |
| **Code** | `stages/review.py` |

1. Checks the diff fingerprint still matches `verified_diff`.
2. Runs **two lenses**: **correctness** and **conventions**.
3. Combines both into `07-review.md`.
4. Any `CHANGES_REQUESTED` → **NEEDS_FIX**. Both `APPROVED` → **DONE**.

---

## 2.8 Retro

**Goal:** you check the result, and Claude proposes improvements to skills or your KB.

| | |
|---|---|
| **Runs as** | **Interactive**, with a real terminal |
| **Model / effort** | sonnet / medium |
| **Repo access** | none (only sees `diff.patch`) |
| **Network** | Anthropic only |
| **KB** | yes, read-only |
| **Skills** | **all** workflow skills at `~/skills`, read-only |
| **Reads** | `06-verify.md`, `07-review.md`, `diff.patch`, `feedback.md` (optional) |
| **Writes** | `08-retro.md` |
| **Code** | `stages/retro.py` |

Claude **proposes** diffs for skills or the KB in `08-retro.md`. It can't apply them.

---

## 2.9 Pseudo-steps (no stage of their own)

### Approval gate

After each DONE stage: `[c]ontinue / [r]etry stage / [a]bort`. See doc 1, section 1.2.

### Fix choice

After NEEDS_FIX: `[f]ix in Implement / [c]ontinue anyway / [a]bort`. See doc 1, section 1.3.

### Escalation Q&A

- Runs when Plan or Implement wrote a non-empty `blocked-questions.md` (`pipeline.py:88`).
- Starts an **interactive** Claude with the Q&A settings, read-only on the **ticket worktree**.
- Succeeds only if `03-qa.md` got **new text at the end**.

### Finalize (after Retro → continue)

Code: `pipeline.py:140`.

1. Checks the diff still matches `verified_diff`.
2. `git add -A` + `git commit --no-verify -m "<TICKET>: implement plan"` in the worktree. `--no-verify` skips the repo's git hooks (`commit_no_verify`, default true).
3. Checks again that the worktree is clean and the diff is unchanged.

**Result:** **one commit** on branch `<ticket-lowercase>`. The workflow **never pushes**, fetches, or opens an MR.
