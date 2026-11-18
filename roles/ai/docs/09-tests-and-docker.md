# 9. Tests, Docker stack and database (design notes)

Status: **design approved, not built yet.** Plan: `10-plan-tests-docker.md`.

This doc holds the facts, the user's answers, the proposed design and the open questions. Update it when a question is answered.

---

## How tests run in `dyflexis-monorepo`

Given by the user:

| Name | Runs in | How |
|---|---|---|
| phpstan | flake | `cd legacy && vendor/bin/phpstan analyze Core Common app src --memory-limit=-1 -c phpstan.neon.dist` |
| Old frontend unit tests | flake | `cd legacy/app && pnpm run test` (Jest) — see note below |
| New frontend unit tests | flake | `cd frontend && pnpm run test:unit` (Vitest) |
| Backend unit tests | flake | `cd legacy && vendor/bin/phpunit --config=phpunit.xml.dist` |
| Backend tests via script | docker | `./test_runner.sh help` (unit, integration, api, mobile-api, codecept-build, acceptance) |
| Website | docker | `https://dyflexis.dev.wodanbrothers.com/dyflexis/` |

- **Start the stack:** `docker compose --profile=dyflexis up -d` from the repo root.
- **One stack at a time** because of port conflicts (80, 443, 3306, 6379, …). Fine for now: we run one ticket at a time.
- **Flake:** `~/.dotfiles/templates/latest/flake.nix` (the repo's `.envrc` does `use flake ~/.dotfiles/templates/latest`).

---

## Facts found in the code

- **`legacy/app` uses pnpm, not npm.** `legacy/app/package.json` has `"npm": "disabled"` and the `test` script is `jest`. The user wasn't sure; `pnpm run test` is inferred, **not yet run**.
- **phpstan needs no database.** `.envrc` sets `PHPSTAN_DBA_URL`, but nothing in `legacy/` (outside `vendor/`) uses it. Verified by grep.
- **phpstan cache is lost every run.** phpstan keeps its cache in the system temp folder. In the sandbox `/tmp` is thrown away. *Not sure* that phpstan follows `$TMPDIR`; check before relying on it.
- **Docker runs the code of the folder it was started from.** `legacy-web-debug` bind-mounts `./legacy` to `/app` (`docker-compose.yml`, `legacy-web-debug.volumes`). So the stack must be started from the **worktree**, not the main checkout.
- **Codeception reseeds `test_customer`** before each run (`test_runner.sh`, `seed_codeception_db_if_atlas`). The user confirmed this is a separate database, only for automated tests. **Safe.**
- **Stage order:** Implement → Verify → Review. A Review finding sends the ticket back to Implement (`pipeline.py`).
- **Today:** Verify has no network (`sandbox.py`, `--unshare-net`). Implement can reach only Anthropic hosts (`net_proxy.py`). `verify_commands`, `flake_path` and `shared_dependencies` are all empty by default (`config.py`).

---

## Decisions (user's answers)

1. **Start the stack from the worktree** with a fixed project name (`-p`). Restarting it there is fine and fast enough.
2. **The workflow starts the stack** (`docker compose --profile=dyflexis up -d`).
3. **Reseeding `test_customer` is safe.**
4. **No untracked files** from the main checkout are needed by Docker (user thinks so; verify on the first real run).
5. **Migrations: manual for now.** Claude may only edit or add table files in `legacy/app/atlas-migrations/customer/schema/tables`. The user checks and runs the migration. → backlog.
6. **Which tests run:**
   - always the tests that were **created or edited** (TDD);
   - **Plan** writes a short list of tests to run;
   - **Review** can suggest extra tests it thinks will fail.
7. **Only affected tests.** phpstan takes minutes, faster with a warm cache.
8. **phpstan on changed files** is fine most of the time. A full run is also quick with cache.
9. **No extra CI checks for now** (no php-cs-fixer, eslint, … yet). Goal stays: pipeline green on push.
10. **Playwright (`playwright/`) is out of scope.** It belongs to the QA team.
11. **Flake:** `~/.dotfiles/templates/latest`.
12. **`legacy/app` command:** user not sure → use `pnpm run test` (see facts).
13. **Browser testing on the dev website: next step.** → backlog.

---

## Security concern: Docker

- **Docker socket = root on the host.** Claude must **never** reach Docker from the sandbox.
- **The worktree is written by Claude.** If the host runs the worktree's `test_runner.sh` or builds from its `docker-compose.yml`, Claude's edits run **outside the sandbox**, possibly as root.
- **Remaining risk (accept knowingly):** Claude-written PHP tests run inside the `legacy-web-debug` container, which has network access. That is a container, not the host.

---

## Design (approved)

### 1. One test list per ticket: `tests.txt`

One command per line, tagged with where it runs:

```text
flake: cd legacy && vendor/bin/phpunit --config=phpunit.xml.dist tests/Unit/FooTest.php
flake: cd frontend && pnpm run test:unit src/foo.spec.ts
docker: api SomeCest
```

- **Plan** writes it.
- **Review** may add lines under `# suggested by review`. Each one also counts as a finding, so the normal fix round runs.
- A `docker:` line holds **only the arguments** for `test_runner.sh`. The workflow validates them (allowed test type, no shell characters) and runs the script itself, without a shell.

### 2. Fixed checks (`verify_commands`)

- phpstan on the **changed PHP files**. Nothing else for now.

### 3. Implement (sandbox, no Docker)

- Write the tests first, then run the `flake:` lines.
- Prompt rule: migrations only as edits in `legacy/app/atlas-migrations/customer/schema/tables`, never run them.

### 4. Verify

- **Step 1 (sandbox, no network):** fixed checks + all `flake:` lines.
- **Step 2 (host):**
  1. **Docker guard:** if the diff touches `test_runner.sh`, `docker-compose.yml`, `.env*`, `legacy/docker/**`, `nginx-proxy/**` or any `Dockerfile` → skip Docker tests and ask the human.
  2. `docker compose -p <fixed name> --profile=dyflexis up -d` from the worktree; wait until healthy.
  3. Run each `docker:` line via `./test_runner.sh`.
- All output goes to `06-verify.md`. A failure → back to Implement (as today).

### 5. Config for the monorepo

- `flake_path`: `~/.dotfiles/templates/latest`
- `shared_dependencies`:
  - `legacy/vendor` ↔ `legacy/composer.lock`
  - `legacy/app/node_modules` ↔ `legacy/app/pnpm-lock.yaml`
  - `frontend/node_modules` ↔ `frontend/pnpm-lock.yaml`
  - `tools/vendor` ↔ `tools/composer.lock`
- A **persistent phpstan cache per ticket** (a `$TMPDIR` kept across Implement, Verify and fix rounds).

### Why

- **The host runs Docker, not Claude**, because socket access = root.
- **The guard** is the simplest fix for a Claude-edited `test_runner.sh` or compose file. Those rarely change in a normal ticket.
- **One test list file** fits TDD: Plan names the tests, Review adds to it, Verify reads it without guessing.

---

## Answers, round 2

1. **Docker guard: yes.** A ticket touching Docker files → the human runs those tests by hand.
2. **Keep the stack up** until a different worktree needs it.
3. **Verify output: show passing and failing tests**, so Claude can see the tests really ran.
4. **phpstan in Implement: the agent decides.** It **always** runs in Verify.
5. **Design approved.** Plan: `10-plan-tests-docker.md`.

---

## Design details added while planning

- **Same compose project name as the user's own stack** (config `docker.project_name`). Then `up -d` from another worktree just recreates the containers with the new mounts, and the database volume is shared. Side effect: after a ticket, the dev website shows the **worktree's** code until the user runs `up -d` from the main checkout again.
- **`.env` comes from the main checkout, never from the worktree.** `.env` is gitignored and holds secrets (API tokens), so it is **not** copied into the worktree (Implement could read it). The host passes it with `--env-file` and `COMPOSE_ENV_FILES`.
- **The guard also checks ignored files.** A gitignored `.env` or `docker-compose.override.yml` in the worktree would change what compose runs, and the normal diff does not show it.
- **Separate phpstan caches for Implement and Verify**, outside the ticket's notes folder. Otherwise Implement could edit Verify's cache and make it pass falsely.
- **Changed files for phpstan:** the host writes the list (`.git` is hidden in the sandbox) and passes its path as `$CW_CHANGED_FILES`.

### Still to confirm on the first real run

- phpstan keeps its cache under `$TMPDIR` (inferred, not checked).
- `docker compose up -d --wait` works with the one-shot services (`ca-bundle`, `object-storage-fixture`).
- `COMPOSE_ENV_FILES` is read by `docker compose exec` (Compose 5.4.0 is installed).
- Where `HOST_UID` / `HOST_GID` come from (not in `.env.dist`, not in the dotfiles).
- `cd legacy/app && pnpm run test` works.
- Untracked folders the stack mounts (`nginx-proxy/certs`, `legacy/cache`) are missing in a fresh worktree. Decision 4 ("no untracked files needed") may be wrong for these.
- The compose **project name** of the user's own stack (to set `docker.project_name`).

---

## Backlog (later)

- **Automate migrations.** Today Claude only edits schema table files; the user runs the migration. There are rules around migrations to work out first.
- **Browser / manual testing** on `https://dyflexis.dev.wodanbrothers.com/dyflexis/` (tool, test login, automatic or human check). **Next step after the tests.**
- **Parallel tickets.** Needs one Docker stack per ticket without port conflicts.
- **More CI checks** (php-cs-fixer, eslint, stylelint, type check) to keep the pipeline green.
- **Playwright** failures from the QA suite: only when they turn our pipeline red.
