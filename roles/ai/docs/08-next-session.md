# 8. Handoff for the next session

Read this first in a new session. It says **where we are**, **what is next**, and **the rules**.

This is the **only status page**. The other docs hold details; their checkboxes are not kept up to date.

---

## Status of every plan (2026-11-19)

| Doc | What | Status |
|---|---|---|
| `06-bugs.md` | Bug list from the first review | **Done**, except "left for later" (see below) |
| `07-plan.md` | Fixes for those bugs (15 tasks) | **Done** (checkboxes never ticked). Intake validated by the user (`ec9fb7f`) |
| `09-tests-and-docker.md` | Design: tests, Docker stack, security rules | **Built**; the format parts are replaced by `11` |
| `10-plan-tests-docker.md` | Tests + Docker plan | **Tasks 1-6 done** (commit `f1b50ed`, 199 tests). **Task 7 not done** → moved into `11`, Task 6 |
| `11-plan-commands-config.md` | Named commands, kebab-case config (global + per repo), `full-configs/` render, new `tests.txt` | **Tasks 1-5 done** (296 tests). Docker parts **unsafe** (bind-mount escape) → see `12` |
| `12-docker-isolation-options.md` | Option 1 (no Docker for Claude) vs option 2 (separate user + rootless Docker) | **Option 2 chosen** (2026-11-19). Last section: running both stacks at once = a later follow-up |
| `13-plan-rootless-docker.md` | Option 2: `cw-docker` user, rootless daemon, `docker-host` + `worktree-base` config, socket override | **Task 1 (NixOS) + Task 2 (spike) done** 2026-11-20, verdict go (results at the end of `13`). **Next: Phase B (Tasks 3-6)**. Branch `ai/option2-rootless-docker`, worktree `~/.dotfiles-option2` |

**Not yet verified anywhere:** a full run on a real ticket, stages Explore → Retro on the real repo, and anything with the real Docker stack.

---

## What is next

1. **Task 6 of `11`:** real-repo checks with the user, then a first real ticket.
   - Confirm `docker-compose.services` (`legacy-web-debug`, `lighttpd`, `db`, `redis`): **not verified without Docker**.
   - Check that the proxy starts with only the `*.crt` files.
   - Check `cs-check` (`bin/cs <changed files>`) and `phpstan:changed` (tests excluded) on a real diff.
   - Read the `docker compose up` section in `06-verify.md` after the first real run.

### Final-review fixes of `11` (done 2026-11-19)

- **New symlinks stop the host.** Before `up` and before every host command: any touched or gitignored path (or a parent folder) that is a symlink not in the base commit → **`NEEDS_HUMAN`**. Root Docker would follow a symlinked mount source.
- **`cs-check`** runs `bin/cs {{files}}` on the **changed files** (skipped when none). The old `bin/cs verify` checked nothing.
- **A missing `repository/<repo-name>.config.json` is an error** (run, `config check`, `config render`, `sandbox_shell`).
- A command that **can't start** is a `FAIL`, not a crash. An **invalid `pattern` regex** is a config error.
- `phpstan:changed` also excludes `tests/*`. `06-verify.md` shows the **`up` output** also when `up` passes.

### Open user decisions

None. Decided 2026-11-19: cs-check in the sandbox with a throwaway git dir; certs crt-only; `~/.npmrc` kept out of containers (start only the needed services); `.env` may reach containers, with a sandbox deny rule. Details: `11`, decisions 9-12.

---

## Rules (keep these)

- **Scope:** only `roles/ai`. **One ticket at a time.** Keep the skills simple.
- **Git:** `git add` and commit are allowed again (2026-11-19). Never push.
- **Secrets:** a deny rule blocks reading `~/.claude/.credentials.json`. Don't work around it.
- **Connections:** don't add new ones (no claude.ai connectors). Use what the repo already has.
- **Tools:** install via Nix only (`nix shell nixpkgs#…`).
- **New files** must be `git add`-ed before a Nix flake build sees them.
- **Config files** live in `roles/ai/configuration/workflows/config/`: `global.config.json`, `repository/<repo-name>.config.json`, `example.config.json`, `config.schema.json`. Neovim validates them live via `$schema`.

---

## Useful commands

Run the unit tests (from `roles/ai/configuration/workflows/workflow/`):

```sh
nix shell --impure --expr 'with (builtins.getFlake "nixpkgs").legacyPackages.${builtins.currentSystem}; python312.withPackages (p: [ p.pytest p.jsonschema ])' -c env PYTHONPATH=. pytest -q
```

Check a config against the schema (from `roles/ai/configuration/workflows/config/`):

```sh
nix shell nixpkgs#check-jsonschema -c check-jsonschema --schemafile config.schema.json repository/dyflexis-monorepo.config.json
```

Build home-manager (also runs the unit tests), from the dotfiles root:

```sh
nix build '.#homeConfigurations."joey@work".activationPackage' --no-link
```

Open a stage's sandbox by hand (from the repo you want to test):

```sh
nix shell nixpkgs#python312 nixpkgs#socat nixpkgs#bubblewrap -c \
  python ~/.dotfiles/roles/ai/configuration/workflows/workflow/tools/sandbox_shell.py \
  <stage> [--interactive] [--copy-credentials] [-- <command>]
```

---

## Backlog

- **Automate migrations** (now: Claude only edits `legacy/app/atlas-migrations/customer/schema/tables`, the user runs it).
- **Browser / manual testing** on the dev website.
- **Dev stack + workflow stack at once** (only **after** option 2 of `12` works): the workflow stack publishes no host ports (`ports: !reset []` override), so Verify no longer stops your dev stack. Research is in `12`, last section.
- **Parallel tickets** (one Docker stack per ticket; per-worktree container names).
- **More CI checks** to keep the pipeline green.
- **Codex / other models** as a runner (needs company OK; start with one read-only Review lens).
- **Deferred minors from plan 10** (all low risk): no `-z` edge-case tests, `.cache/<ticket>` never cleaned up, a few extra asserts.

## Known open items (minor, from `06-bugs.md`)

- The settings file uses a denylist (only `hooks` removed).
- Some edge cases in the fix rounds (`--from-stage implement`, `--only-stage`).
- A Verify timeout loses its partial output.
- `_run_pipeline` and `build_bwrap_command` are long.
