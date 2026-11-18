# 6. Bugs and risks found

Found by reading all code in `roles/ai` and by running a few checks. **Skills are left out** on purpose.

Python paths are relative to `roles/ai/configuration/workflows/workflow/claude_workflow/`.

**Status labels**

- **Verified** = I ran something that shows it.
- **From code** = clear from reading the code, not run.
- **Unsure** = likely, but needs a test. The "Confirm" line says how.

**Already checked and fine:** all 31 tests pass (Python 3.12 + pytest via `nix shell`). Every Claude CLI flag the code uses exists in Claude Code 2.1.322 (`claude --help`).

---

## Status after the fixes (plan `07-plan.md`)

| Bug | Status | How |
|---|---|---|
| H1 terminal | **Fixed, verified** | No `--new-session` for interactive runs; `tty_nr` non-zero in the Q&A sandbox |
| H2 dependencies | **Fixed** (needs a check on a Dyflexis repo) | `deps.py`: read-only mounts from main when lockfiles match |
| H3 reviewer blocker | **Fixed** | Plan review pass checks the blocker |
| H4 empty blocker | **Fixed** | `has_blocker` deletes an empty file |
| H5 verdict | **Fixed** | `parse_verdict` accepts markdown |
| H6 token refresh | **Fixed, verified** | `platform.claude.com` allowed (seen in proxy log); one-way login copy by `expiresAt` |
| M1 repo root | **Fixed** | `repo_root` in `cli.py` |
| M2 plan vs worktree | **Fixed** | Worktree created at Explore |
| M3 ticket case | **Fixed** | Key upper-cased |
| M4 git hooks | **Fixed** | `commit_no_verify` (default true) |
| M5 untracked files | **Improved** | Message lists the changed files |
| M6 env leak | **Fixed, verified** | `--clearenv` + allowlist; `GITHUB_TOKEN` not visible in the sandbox |
| M7 Intake MCP | **Fixed** | Uses the repo's `.mcp.json` server (`Atlassian-Rovo-MCP`) with a one-way copy of `~/.mcp-auth` |
| M8 timeouts | **Fixed** | `headless_timeout`, `verify_timeout` |
| L1 skill folders | **Fixed** | Skills are a system prompt, not mounted |
| L2 plan restart | **Not fixed** (by choice) | See `07-plan.md` |
| L3 escalation repo | **Fixed** | Escalation uses the worktree |
| L4 stale review | **Fixed** | Only `fix_feedback` is read, cleared after Implement |
| L5 hooks in sandbox | **Fixed** | Generated settings without hooks |
| L6 unused files | **Fixed** | Script removed, duplicate skills link removed |
| L7 `nix develop` per call | **Fixed** | Dev shell loaded once per run (`env.py`) |
| Flow: Review → Implement manual | **Fixed** | Fix loop with `max_fix_rounds` |

### Found by the final review, fixed

| Finding | Fix |
|---|---|
| **Critical:** a sandbox could overwrite any host file via a fixed credentials temp name (reproduced) | Random temp file + `os.replace`; symlinks in the sandbox home refused; same for `.claude.json` |
| Proxy log followed symlinks (host file append) | Opened with `O_NOFOLLOW` |
| Sandbox → host credentials copy trusted the sandbox | Removed: login is copied **in** only |
| `shellHook` banner broke the env capture (`bwrap: setenv failed`) | Env written to a file; invalid names skipped |
| Dev shell vars equal to host values were dropped | `nix develop --ignore-environment`, no diff |
| Missing `LOCALE_ARCHIVE`, `TERMINFO`, `TERMINFO_DIRS` | Added to the allowlist |
| `APPROVED WITH CHANGES` counted as approved | Whole line must be the verdict (+ optional `: details`) |
| Lockfile error when main has no such folder | Skip first, then compare lockfiles |

### Found by the final review, left for later (minor)

- Settings use a denylist (only `hooks` removed); an allowlist would be safer, e.g. for `enabledPlugins`.
- `fix_rounds` resets on every `--from-stage implement`; the "out of rounds" error has no next-step hint; `--only-stage` + fix exits 0.
- Interactive argv: the prompt comes after list flags; a `--` before it would be safer.
- A Verify timeout throws away the partial output.
- Readability: `_run_pipeline` and `build_bwrap_command` are long; `stage_runners is None` is used as a "real run" switch.

---

## High

### H1. Interactive stages have no controlling terminal — **Verified**

- **Where:** `sandbox.py:172` (`--new-session`), used by Q&A, Retro, escalation Q&A.
- **What:** inside the sandbox, `/proc/self/stat` shows `tty_nr=0` and opening `/dev/tty` fails ("No such device or address").
- **Effect (unsure how bad):** window resize signals do not reach Claude, Ctrl-C may not give exit code 130, so the "resume session" path in `stages/qa.py:58-61` may never trigger. Tools that open `/dev/tty` fail.
- **Why the flag is there:** it blocks the TIOCSTI terminal injection attack. That attack is **already disabled** on this kernel (`/proc/sys/dev/tty/legacy_tiocsti` = `0`).
- **Fix idea:** drop `--new-session` for interactive runs only.
- **Confirm:** `python tools/sandbox_shell.py qa --copy-credentials -- claude`, then resize the window and press Ctrl-C.

### H2. Verify cannot work without dependencies — **From code**

- **Where:** `git_host.py:39-71`, `stages/verify.py`.
- **What:** the worktree is a fresh checkout, so `vendor/` and `node_modules/` are missing. Verify has no network, so it cannot install them.
- **Effect:** PHPUnit, ESLint, etc. fail in Verify and in Implement.

### H3. A plan reviewer's `blocked-questions.md` leaks into Implement — **From code**

- **Where:** `stages/plan.py:63` (review pass uses `run_claude_headless`, not the blocker check), `pipeline.py:223-224`.
- **What:** if the reviewer writes `blocked-questions.md`, Plan ignores it. The file stays. After you approve Plan, **Implement is "blocked" right away** with the plan reviewer's questions.

### H4. An empty `blocked-questions.md` blocks the ticket for good — **From code**

- **Where:** `pipeline.py:59-60`, `pipeline.py:223-224`, `pipeline.py:235-237`.
- **What:** an empty blocker file still counts as "blocked". The escalation then returns False ("no questions"), so the run exits 1 and **the file is not deleted**.
- **Effect:** every rerun fails again at once until you delete the file by hand.

### H5. The verdict check is too strict — **From code**

- **Where:** `stages/plan.py:74-78`, `stages/review.py:85-87`.
- **What:** the first line must be exactly `APPROVED` or `CHANGES_REQUESTED`. A first line like `# APPROVED`, `**APPROVED**`, or `APPROVED.` gives **"Invalid verdict" → FAILED**.
- **Effect:** LLMs often add markdown to the first line. Expect random failures.

### H6. The token refresh may be blocked in offline stages — **Unsure**

- **Where:** `net_proxy.py:12` (allowlist = `api.anthropic.com` only), `sandbox.py:141-149` (credentials copied once per ticket).
- **What:** Q&A, Implement, Review and Retro only reach `api.anthropic.com`. If the OAuth token expires, the refresh call probably goes to **another host** and gets 403. Also, the sandbox copy and the host copy refresh separately, so one may invalidate the other.
- **Confirm:** add logging to the proxy (it logs nothing now), and run a stage with an expired token.

---

## Medium

### M1. `repo_path` is the current folder, not the git root — **From code**

- **Where:** `config.py:167`, `pipeline.py:164-166`.
- **What:** running from a subfolder mounts only that subfolder for Explore/Q&A/Plan. Resuming from a **different folder** fails with "Checkpoint belongs to another repository".
- **Fix idea:** resolve with `git rev-parse --show-toplevel`.

### M2. The plan is based on different code than the worktree — **From code**

- **Where:** `stages/explore.py:22-28`, `stages/plan.py:28-34`, `stages/implement.py:26`.
- **What:** Explore and Plan read your main checkout's **working tree** (including uncommitted changes, any branch). Implement branches from `HEAD` of that checkout **at the moment Implement starts**. Nothing is fetched first.
- **Effect:** if you switch branches or have local changes between Plan and Implement, the plan doesn't match the code.

### M3. Ticket key case is not normalized — **From code**

- **Where:** `pipeline.py:129`, `stages/implement.py:24-25`.
- **What:** `PROJ-123` and `proj-123` get **two state folders** but the **same branch** `proj-123`. The second run fails in `git worktree add` (branch already checked out).

### M4. Host git hooks run during Finalize — **Unsure**

- **Where:** `pipeline.py:108-112`, `git_host.py:114-120`.
- **What:** `git commit` runs on the host, so the repo's pre-commit hooks run too. A hook that **fails** means exit 1. A hook that **reformats files** gives a "dirty after commit" or "commit changed the verified diff" error.
- **Confirm:** check if the Dyflexis repos use husky, grumphp, lint-staged or similar.

### M5. Verify fails if tests create untracked files — **From code**

- **Where:** `stages/verify.py:70-73`, `git_host.py:89-92`.
- **What:** new untracked files that are **not gitignored** (coverage report, `.phpunit.result.cache`, …) change the diff, so you get **"Verification changed the worktree diff"**.

### M6. The host environment leaks into the sandbox — **From code**

- **Where:** `sandbox.py:169-182` (no `--clearenv`).
- **What:** all your environment variables (API tokens, etc.) are visible inside. Intake, Explore and Plan also have **full internet** and `WebFetch`.
- **Effect:** a malicious ticket or web page could make Claude send them out (prompt injection).

### M7. The Intake MCP check only knows one setup — **From code**

- **Where:** `stages/intake.py:26-39`, `config.json` (`mcp__atlassian__*`).
- **What:** only a **top-level** `mcpServers.atlassian` in `~/.claude.json` passes. Project-scoped servers and claude.ai connectors (e.g. "Atlassian Rovo") fail the check. Their tool names also don't match `mcp__atlassian__*`.

### M8. Commands have no timeouts — **From code**

- **Where:** `stages/verify.py:56`, `claude_runner.py:90`.
- **What:** a hanging test or a stuck headless Claude **hangs the workflow forever**.

---

## Low

### L1. Old skill folders stay in the sandbox — **Verified**

- **Where:** `sandbox.py:226-229`.
- **What:** bwrap creates empty mount-point folders in the ticket's fake home. In the Q&A sandbox I saw `~/.claude/skills/explore/` (empty) next to `qa/` and `shared/`. It's harmless, but not the "only my stage" view.

### L2. An escalation during plan revision restarts Plan from scratch — **From code**

- **Where:** `stages/plan.py:85-90`, `pipeline.py:241`.
- **What:** after the escalation, Plan re-runs from the **draft**. The revision work and the review pass count are lost.

### L3. Implement's escalation Q&A looks at the main checkout — **From code**

- **Where:** `pipeline.py:67-73`.
- **What:** it mounts `repo_path`, not the worktree. Questions about the new code can't be checked against it.

### L4. A stale review is reused after re-planning — **From code**

- **Where:** `stages/implement.py:50-56`.
- **What:** after `--from-stage plan`, Implement still reads the old `07-review.md` from the previous plan.

### L5. Hooks from `settings.json` fail inside the sandbox — **From code**

- **Where:** `sandbox.py:198-206` mounts `~/.claude/settings.json`.
- **What:** the `notify-send` hooks run in every sandbox, which has no D-Bus. They fail on every Stop/Notification. This is noise, not a blocker.

### L6. Unused or duplicate files — **From code**

- `configuration/scripts/claude-workflow.sh` is not used anywhere.
- Skills are installed twice. `ai.nix:53-56` links them to `~/.config/claude-workflow/skills`, but the wrapper sets `CLAUDE_WORKFLOW_SKILLS` to the packaged copy (`ai.nix:42`), so the linked copy is never read.

### L7. `nix develop` runs on every call — **From code**

- **Where:** `claude_runner.py:63-66`, `stages/verify.py:54-55`.
- **What:** the flake is evaluated again for every Claude call and every verify command. It's slow, but it works.

---

## Flow notes (by design, but easy to trip over)

- **Review → Implement is manual.** A `CHANGES_REQUESTED` review stops the run. Running it again without `--from-stage implement` reviews the **same diff** again.
- **Retry does not reset the worktree.** Retrying Implement at the gate keeps the earlier changes.
