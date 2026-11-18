# 8. Handoff for the next session

Read this first in a new session. It says **where we are**, **what is next**, and **the rules**.

The other docs (`01`–`07`) hold the details. Read them only when a task needs them.

---

## Where we are

- The workflow `claude-workflow` lives in `roles/ai/configuration/workflows/workflow/`.
- All fixes from `07-plan.md` are **implemented**. 123 unit tests pass, and so does the Nix build.
- **Intake** uses the repo's `Atlassian-Rovo-MCP` server (`.mcp.json`) with a one-way copy of `~/.mcp-auth`. The user has **validated Intake** (commit `ec9fb7f`).
- **Verified by hand:**
  - the Q&A sandbox (terminal, clean env, proxy);
  - the dev shell capture with a test flake.
- **Not yet verified:** a full run on a real ticket, and stages Explore → Retro on the real repo.

---

## What is next

**Current phase: tests + Docker.** The design is approved and in **`09-tests-and-docker.md`** (facts, decisions, backlog). The step-by-step plan is **`10-plan-tests-docker.md`**. Nothing is built yet; start with Task 1 once the user has approved the plan.

The topics are:

1. **Run the real tests** of the main repo (`~/Code/Work/dyflexis-monorepo`) in Implement and Verify:
   - set `verify_commands` and `flake_path` for that repo;
   - check that the `vendor/` and `node_modules/` mounts work (`deps.py`).
2. **Web server and database** for integration, API, e2e and manual browser testing.
   - Verify has **no network at all** today, and Implement can only reach Anthropic hosts.
   - So this needs a design decision first. **Don't build it before the user has explained the setup.**

---

## Rules (keep these)

- **Scope:** only `roles/ai`. **One ticket at a time.** Keep the skills simple.
- **Git:** never commit or push without an explicit OK. The user commits themselves.
- **Secrets:** a deny rule blocks reading `~/.claude/.credentials.json`. Don't work around it.
- **Connections:** don't add new ones (no claude.ai connectors). Use what the repo already has.
- **Tools:** install via Nix only (`nix shell nixpkgs#…`).
- **New files** must be `git add`-ed before a Nix flake build sees them.

---

## Useful commands

Run the unit tests (from `roles/ai/configuration/workflows/workflow/`):

```sh
nix shell nixpkgs#python312 nixpkgs#python312Packages.pytest -c python -m pytest -q
```

Open a stage's sandbox by hand (from the repo you want to test):

```sh
nix shell nixpkgs#python312 nixpkgs#socat nixpkgs#bubblewrap -c \
  python ~/.dotfiles/roles/ai/configuration/workflows/workflow/tools/sandbox_shell.py \
  <stage> [--interactive] [--copy-credentials] [-- <command>]
```

---

## Backlog (from the tests phase)

Details in `09-tests-and-docker.md`.

- **Automate migrations** (now: Claude only edits `legacy/app/atlas-migrations/customer/schema/tables`, the user runs it).
- **Browser / manual testing** on the dev website — next step after the tests.
- **Parallel tickets** (one Docker stack per ticket).

---

## Known open items (minor, deferred)

See `06-bugs.md`, "left for later". In short:

- the settings file uses a denylist (only `hooks` removed);
- some edge cases in the fix rounds (`--from-stage implement`, `--only-stage`);
- a Verify timeout loses its partial output;
- `_run_pipeline` and `build_bwrap_command` are long.
