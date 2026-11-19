# 12. Docker isolation: option 1 vs option 2

**Why this doc:** the final review of plan 11 found that the Docker stack can leak host files to code Claude wrote (see "The problem" below). These are the two ways forward, with what each one costs.

**Time estimates** are my best guess, **not measured**. "Agent time" is the time I (and my subagents) work. "Your time" is what you have to do or wait for. Docker on a new setup often has surprises, so treat option 2's numbers as uncertain.

---

## The problem in short

- Verify starts the compose stack with **root Docker** from the ticket's worktree, and **Claude controls the worktree**.
- Docker **follows symlinks** when it mounts a folder (`./legacy/pub` → `/home/joey` mounts your home).
- Claude's code already runs **while** `docker compose up` creates the containers (composer scripts, `bin/console`, the healthcheck). It can plant such a symlink after any check we do.
- **Result:** Claude-written code could read your files (`~/.ssh`, tokens) and, with a race, write them (`~/.zshrc`).
- **Root cause:** the Docker daemon (root) can reach your home folder. As long as that is true, a check in Python is whack-a-mole.

---

## Option 1: no Docker for Claude (for now)

### What it means

- Verify only runs **`sandbox` commands**: phpstan, phpunit, cs-check, the frontend unit tests.
- **`host` and `container` commands are switched off**, and so is the compose stack. Claude never starts or touches Docker.
- **Integration, API and acceptance tests** (Codeception via `test_runner.sh`) are **not run by the workflow**. They still run in the **GitLab pipeline**.
- You keep using your own dev stack exactly as now.

### What changes

- **Config:** a global switch, e.g. `"docker-enabled": false` (default `false`). While it is off:
  - `config check` refuses `host`/`container` commands and `needs-compose-stack`;
  - Plan, Implement and Review don't see those commands in their catalogue, so Claude only plans unit tests.
- **Repo config:** `tests:integration`, `tests:api`, `composer-install` and `docker-compose` stay in the file, but are inactive. Turning the switch on later brings them back.
- **No code is deleted.** Everything from plans 10 and 11 stays, ready for option 2.

### What it does not solve

- Changes that only integration/API tests catch are found **in CI, after the push**, not before.

### Time

| Part | Agent time | Your time |
|---|---|---|
| Switch + config check + catalogue filter + tests + review | **~1 hour** | review the diff (~10 min) |
| Task 6, sandbox part: phpstan, phpunit, cs-check, frontend tests on the real repo | ~1 hour | be there to approve steps (~30-60 min) |
| **Total** | **~2 hours** | **~1 hour** |

**Risk:** low. All parts are already built and reviewed; this only switches things off.

---

## Option 2: the stack runs as a separate user (rootless Docker)

### The idea

- Create a **separate Linux user**, e.g. `cw-docker`, with its **own rootless Docker daemon**.
- The workflow's compose stack runs **only in that daemon**.
- **Rootless** means the daemon and every container run as `cw-docker`, not as root ([Docker docs: rootless mode](https://docs.docker.com/engine/security/rootless/)).
- Your home folder is `700` (only you can read it). So when Claude's code plants `legacy/pub → /home/joey`, the mount **fails with "permission denied"**. The protection comes from **Linux file permissions**, not from our Python checks.

### What it needs

**NixOS config** (in `hosts/work` / a role; you run `nixos-rebuild switch`, since that needs `sudo`):

- the user `cw-docker`, with its own systemd user session kept alive ("linger");
- rootless Docker for that user. NixOS has `virtualisation.docker.rootless`, but **I'm not sure** it works for a second user without extra systemd setup; checking that is the first step;
- **ports 80/443:** rootless Docker can't bind ports below 1024 by default. We need the sysctl `net.ipv4.ip_unprivileged_port_start=80` (system-wide), or the stack must use other ports;
- a **shared folder for worktrees** outside your home, e.g. `/srv/claude-workflow/worktrees`. The group is shared by you and `cw-docker`, with default ACLs, so both can read and write.

**Workflow code:**

- `worktree_base` moves to the shared folder (today it is under `~/Code/Worktrees`, which `cw-docker` can't reach);
- every `docker` / `docker compose` call gets `DOCKER_HOST=unix:///run/user/<cw-docker uid>/docker.sock`. You need access to that socket (group permission);
- `HOST_UID` / `HOST_GID` for the compose file and `test_runner.sh` are set to fit the rootless user mapping;
- **file ownership:** files that containers write into the worktree (`legacy/cache`, Codeception output) get owned by `cw-docker`. The shared group + ACLs must keep them editable for you and the sandbox;
- the plan-11 guard, base-copy and symlink checks **stay** as extra layers.

**One-time setup for `cw-docker`:**

- **log in to the GitLab registry** (`registry.gitlab.com/dyflexis/...` images are private). That token lives in `cw-docker`'s Docker config, readable by the daemon but not by containers;
- **pull/build all images again.** The new daemon has its own image store, so this costs disk space and time on the first run.

### How it works with your dev stack

- **Two daemons:** your normal root Docker (your dev stack) and `cw-docker`'s rootless Docker (the workflow).
- They are **separate**, so a Verify run can't "take over" your containers anymore. Both stacks want ports 80/443, so **Verify must stop your dev stack first** (`docker compose down` on your daemon). Or you move your dev stack to the rootless daemon too, if you want one stack again.
- **Databases are separate** (separate volumes). For the tests that's fine: `test_customer` is seeded on every run.

### Variant: a small VM instead of a user

- The same idea, but the stack runs in a NixOS VM (e.g. `microvm.nix`), with the worktree shared into it.
- **Stronger** (a separate kernel) but **heavier**: VM setup, file-sharing speed, more memory.
- I'd only go there if the separate user turns out not to work.

### What it does not solve

- Containers still **run Claude's code with network access**. That was accepted in `09`.
- `.env` values still reach the containers. You said that's fine.
- Anything **world-readable on the host** (`/etc`, the Nix store) stays readable, as it is for any user.

### Time

| Part | Agent time | Your time |
|---|---|---|
| Short plan + check the NixOS rootless options for a second user | ~1 hour | read and approve the plan (~15 min) |
| NixOS config: user, rootless daemon, socket access, sysctl, shared worktree folder | ~1-2 hours | `nixos-rebuild switch` + test it (~30 min) |
| Workflow code: `DOCKER_HOST`, worktree location, UID/GID, permissions + tests + reviews | ~2-3 hours | review the diffs (~30 min) |
| First real run: registry login, image pull/build, debugging rootless + compose + ports | ~1-3 hours (**most uncertain**) | be there for Docker steps; image download time (~20-40 min, guess) |
| Task 6 checks (sandbox + Docker parts), incl. the symlink test that must now fail with "permission denied" | ~1-2 hours | ~1 hour |
| **Total** | **~6-11 hours, over 2-3 sessions** | **~3-4 hours** |

**Risk:** medium.

- **Rootless Docker + this compose file is untested.** Things that could need workarounds: `docker.sock` mounts in `proxy`/`proxy-companion`, ports 80/443, file ownership in the worktree, the private registry.
- **If it doesn't work out,** the fallback is the VM variant. That adds roughly another 4-8 hours (guess).

---

## Main functional differences

| | **Option 1: no Docker for Claude** | **Option 2: separate user + rootless Docker** |
|---|---|---|
| **Tests the workflow runs before a push** | Unit tests, phpstan, cs-check, frontend unit tests | The same **plus** integration, API and acceptance tests |
| **Tests left to CI only** | Integration, API, acceptance | Only what the workflow doesn't list (e.g. Playwright) |
| **Can Claude-written code reach your home folder?** | No: it only runs in the bwrap sandbox | No: the Docker daemon itself can't reach it (file permissions) |
| **Where the protection comes from** | Docker is never started | Linux permissions, plus the plan-11 checks as extra layers |
| **Your dev stack** | Untouched | Separate; Verify stops it first (ports 80/443), or you move it to the rootless daemon |
| **System changes** | None | New user, rootless daemon, a sysctl for low ports, a shared worktree folder |
| **Ongoing maintenance** | None | A second image store (disk), registry login for `cw-docker`, keeping two daemons |
| **Speed of a Verify run** | Fast (no stack) | Slower: stack start, plus image builds on the first run |
| **Agent time to finish** | **~2 hours** | **~6-11 hours** (uncertain) |
| **Your time** | **~1 hour** | **~3-4 hours** |
| **Can be undone / combined** | Yes: option 2 can be added later; it only turns the switch on | Yes: the switch from option 1 is still useful to turn Docker off per repo |

### My recommendation

- **Do option 1 now.** It's quick, safe, and lets us finally run a **first real ticket**. Most of the remaining risk is in the stages, not in Docker.
- **Do option 2 after that,** as its own plan, once the workflow works end to end with unit tests. The switch from option 1 makes the step to option 2 small and reversible.
