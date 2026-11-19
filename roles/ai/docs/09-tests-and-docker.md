# 9. Tests, Docker stack and database (design notes)

Status: **built, not yet run on the real repo.** Plan: `10-plan-tests-docker.md`; the command format was replaced by plan `11`. The real-repo checks are Task 6 of `11`.

**Update (plan 11):** `flake:` / `docker:` prefixes, `verify_commands` and `flake_path` in `config.json` are gone. Read the section "Named commands (replaces the prefixes)" below first. The older sections keep the original reasoning and may use the old names.

This doc holds the facts, the user's answers, the proposed design and the open questions. Update it when a question is answered.

---

## Named commands (replaces the prefixes)

**The idea:** every check is a **named command** in the repo config. `tests.txt` lists names, not shell lines.

- **Config:** `repository/dyflexis-monorepo.config.json`, key `commands`. Schema: `config.schema.json`.
- **`run-in`** decides where it runs: `sandbox` (bwrap, no network), `host` (after the guard), or `container` (`docker exec`).
- **`tests.txt` line:** `<command> [key=value ...]`, for example `tests:api filter=InvoiceCest.php`.
- **`verify`** lists what Verify always runs, in order.

**Safety rules for `tests.txt` values** (Claude writes the file):

- A parameter needs a **`pattern`**, and the whole value must match it.
- A value word may **not start with `-`** (no options) and may **not contain a `..` path segment**.
- Values are **shell-quoted word by word**. A value with spaces becomes several arguments, never shell syntax.
- A `host` command's script is **protected like the compose files**, and the **base-commit copy** runs.

### Decisions 9-12 (user, 2026-11-19)

9. **`cs-check` runs in the sandbox** as `bin/cs {{files}}`, with **`needs-git: true`**. `files` defaults to **all changed files**; none changed means **skipped**. A throwaway `git init` folder replaces the masked `.git`.
10. **`config render`** writes the merged config to `full-configs/<repo>.config.json` (gitignored, read-only view). The workflow never reads it.
11. **Certs: copy only `*.crt`.** A `host-copies` entry is `{"path": "nginx-proxy/certs", "include": ["*.crt"]}`. Private keys stay behind. Symlinks are skipped. *To confirm in Task 6:* the proxy still starts.
12. **Secrets:**
    - `docker-compose.services` lists the services the tests need: `legacy-web-debug`, `lighttpd`, `db`, `redis`. Only those and their `depends_on` start. This also skips the `pnpm install` containers that bind-mount `~/.npmrc`. **Not verified without Docker: confirm in Task 6.**
    - The repo `.env` may reach containers.
    - The generated sandbox Claude settings **deny reading** `Read(**/.env)` and `Read(**/.env.*)` (defence in depth; `.env` is not mounted anyway).

### `phpstan:changed`

- A separate command: phpstan on the **changed PHP files**, tests (`*Test.php`, `*/Tests/*`, `tests/*`) excluded. `legacy/tests/` holds the Codeception `Cest` files. No changed file means **skipped**.
- It is **not** in `verify`.

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
- A **persistent phpstan cache per ticket**, kept across fix rounds. **Implement and Verify each get their own cache**; `flake:` lines get none (see "Built").

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
- **Separate phpstan caches for Implement and Verify**, outside the ticket's notes folder. Implement cannot edit Verify's cache directly.
  - This is **defence in depth**, not a full fix: `phpstan.neon.dist` and its bootstrap files live in the worktree, so Implement still controls how phpstan runs.
- **Changed files for phpstan:** the host writes the list (`.git` is hidden in the sandbox) and passes its path as `$CW_CHANGED_FILES`.

### Still to confirm on the first real run

- phpstan keeps its cache under `$TMPDIR` (inferred, not checked).
- `docker compose up -d --wait` works with the one-shot services (`ca-bundle`, `object-storage-fixture`).
- `COMPOSE_ENV_FILES` is read by `docker compose exec` (Compose 5.4.0 is installed).
- Where `HOST_UID` / `HOST_GID` come from (not in `.env.dist`, not in the dotfiles).
- `cd legacy/app && pnpm run test` works.
- Untracked folders the stack mounts are missing in a fresh worktree, so decision 4 was wrong for these:
  - **`nginx-proxy/certs`** (user confirmed): the host copies it from the main checkout before `up`, and every sandbox hides it (it may hold a CA private key);
  - **`legacy/cache`** (user not sure; the app rebuilds it on a branch switch): the host only creates the empty folder.
- **Project name: `dyflexis-monorepo`** (confirmed with `docker compose ls`).

---

## Built (what the code does)

- **Config** (`config.json`): flake, phpstan `verify_commands`, 4 shared dependencies, and `docker` with project `dyflexis-monorepo`, profile `dyflexis`, `host_copies` = `nginx-proxy/certs`, `create_dirs` = `legacy/cache`.
- **The host runs the base commit's copy of `test_runner.sh`**, never the worktree's file.
- **The guard is re-checked before every `docker:` line**, not only once.
- **`flake:` lines get no persistent cache.** Only `verify_commands` (phpstan) use the Verify cache.
- **A Docker stop asks the human.** When the guard trips, the guard check fails, or preparing the worktree fails, Verify returns **`NEEDS_HUMAN`**:
  - `06-verify.md` is still written, with the sandbox and `flake:` results and a "Docker tests skipped" section;
  - the pipeline asks **`[c]ontinue / [r]etry stage / [a]bort`**. Continue marks Verify done and goes on to Review;
  - with **`--auto`** it stops (exit 1). Run again without `--auto` to continue or retry.
- **No new symlinks (final review of plan 11).** Root Docker follows a symlinked bind-mount source. If Claude replaced `./api-documentation` with a link to `$HOME`, Docker would mount `$HOME` into a test container.
  - Right before `up` and before **every** host command, the host checks every touched or gitignored path, **and each parent folder** of it, with `lstat`.
  - A symlink stops the run (**`NEEDS_HUMAN`**), unless the base commit has the **same symlink with the same target** at that path.
  - Any doubt (an `lstat` error, an odd path) also stops. Code: `docker_stack.symlink_violations`.
- **`06-verify.md` shows the `docker compose up` output** (command line plus output), also when `up` passes.
- **`up` gets 10 extra minutes** on top of `up_timeout` (images build before `--wait-timeout` starts).
- **The stack is left running** (user decision). After a ticket, the dev site shows the worktree's code until you run `docker compose --profile=dyflexis up -d` from the main checkout.

---

## Known limits

- **Profiles `all` / `storybook` bind-mount the repo root read-write** (`dyflexis-storybook`). A container could change the compose file during a line. **Keep the profile `dyflexis`.**
- **The `migrations` image builds from the worktree's `./legacy` context.** Dockerfiles are protected, but the files copied into the image are not. Build steps run in containers, not on the host.
- **Containers run Claude-written code with network and secrets.** **Needs the user's OK.**
  - The `dyflexis` profile starts **`dyflexis-webpack`** and **`dyflexis-frontend`**. They run `pnpm install` and scripts from the **worktree's `package.json`**, with network access, and bind-mount **`~/.npmrc`**.
  - **`.env` values** (for example `POS_PLATFORM_API_KEY`, `VITE_MAPTILER_API_KEY`) are in the environment of containers that run Claude-written code.
  - Container output can come back to Claude through **`06-verify.md`**.
- **The cert copy failed on the real repo (resolved by decision 11: crt-only copy).** Check in Task 6 that the proxy starts.
  - The keys in `nginx-proxy/certs/*.key` are **`root:root 0600`**, so the host cannot read them and the copy fails. Verify then stops and asks the human (see "Built").
  - Option **(a)**: copy the folder through a root Docker container.
  - Option **(b)**: copy only the `*.crt` files. **Chosen** (decision 11).

---

## Backlog (later)

- **Automate migrations.** Today Claude only edits schema table files; the user runs the migration. There are rules around migrations to work out first.
- **Browser / manual testing** on `https://dyflexis.dev.wodanbrothers.com/dyflexis/` (tool, test login, automatic or human check). **Next step after the tests.**
- **Parallel tickets.** Needs one Docker stack per ticket without port conflicts.
- **More CI checks** (php-cs-fixer, eslint, stylelint, type check) to keep the pipeline green.
- **Playwright** failures from the QA suite: only when they turn our pipeline red.
