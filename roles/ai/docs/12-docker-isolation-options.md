# 12. Docker isolation: option 1 vs option 2

> **Status (2026-11-20): option 2 is built** (plan 13, `13-plan-rootless-docker.md`). Tasks 1-6 are done; the first real run (Task 7) is next. This doc keeps the reasoning. Where it differs from what was built, **`13` and `09` win**: socket `/var/lib/cw-docker-sock/docker.sock`, config keys `docker-host` and `worktree-base`, and no registry login for `cw-docker`.

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

- the worktree base moves to the shared folder (config key `worktree-base`; before plan 13 it was `~/.local/state/claude-workflow/worktrees`, which `cw-docker` can't reach);
- every `docker` / `docker compose` call gets `DOCKER_HOST` (built: config key `docker-host`, socket `unix:///var/lib/cw-docker-sock/docker.sock`). You need access to that socket (group permission);
- `HOST_UID` / `HOST_GID` for the compose file and `test_runner.sh` are set to fit the rootless user mapping;
- **file ownership:** files that containers write into the worktree (`legacy/cache`, Codeception output) get owned by `cw-docker`. The shared group + ACLs must keep them editable for you and the sandbox;
- the plan-11 guard, base-copy and symlink checks **stay** as extra layers.

**One-time setup for `cw-docker`:**

- **registry login (changed in the spike):** `cw-docker` needs **none**. Your own `docker` client logs in (`~/.docker/config.json`) and pulls through the daemon;
- **pull/build all images again.** The new daemon has its own image store, so this costs disk space and time on the first run.

### How it works with your dev stack

- **Two daemons:** your normal root Docker (your dev stack) and `cw-docker`'s rootless Docker (the workflow).
- They are **separate**, so a Verify run can't "take over" your containers anymore. Both stacks want ports 80/443, so **in option 2 Verify must stop your dev stack first** (`docker compose down` on your daemon). Running both at once is a **later step, not part of option 2**: see "Later, after option 2: both stacks at once" at the end.
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
| **Your dev stack** | Untouched | Separate; Verify stops it first (ports 80/443). Running both at once is a later step (see the last section) |
| **System changes** | None | New user, rootless daemon, a sysctl for low ports, a shared worktree folder |
| **Ongoing maintenance** | None | A second image store (disk), keeping two daemons (the registry login is yours, client side) |
| **Speed of a Verify run** | Fast (no stack) | Slower: stack start, plus image builds on the first run |
| **Agent time to finish** | **~2 hours** | **~6-11 hours** (uncertain) |
| **Your time** | **~1 hour** | **~3-4 hours** |
| **Can be undone / combined** | Yes: option 2 can be added later; it only turns the switch on | Yes: the switch from option 1 is still useful to turn Docker off per repo |

### My recommendation

- **Do option 1 now.** It's quick, safe, and lets us finally run a **first real ticket**. Most of the remaining risk is in the stages, not in Docker.
- **Do option 2 after that,** as its own plan, once the workflow works end to end with unit tests. The switch from option 1 makes the step to option 2 small and reversible.

---

## Later, after option 2: both stacks at once (research, 2026-11-19)

> **Not part of option 2.** This is a **separate follow-up**, planned and built only **after option 2 works end to end**.
>
> Until then, option 2 keeps the simple rule: **Verify stops your dev stack first**, and the **sysctl for low ports stays** in option 2. Nothing below is planned or built yet.

**Question:** can we run your dev stack and the `cw-docker` stack **at the same time**, e.g. with Podman?

**Short answer:** **Podman itself does not fix it.** But a separate daemon (rootless Docker *or* Podman) **plus a small compose override** does. So with option 2, both stacks can run side by side.

### What actually conflicts today

Checked with `docker compose --profile dyflexis config legacy-web-debug lighttpd db redis` on the monorepo (the services Verify starts, plus their `depends_on`). Three things clash when two copies run on **one** daemon:

| What | Where | Fixed by a separate daemon? |
|---|---|---|
| **Host ports** `0.0.0.0:80, 443, 3306, 6379, 8333` and `127.0.0.1:8888, 23646` | `proxy`, `db`, `redis`, `seaweedfs` (`docker-compose.yml:54-62`, `:129-133`, `:603-606`) | **No** |
| **Fixed container names** `proxy`, `proxy-companion` | `docker-compose.yml:126`, `:162` | Yes (each daemon has its own names) |
| **Fixed subnet** `172.31.0.0/16` for network `dfs` | `docker-compose.yml:918-922` | Yes, I expect (see "Not sure" below) |

### Why Podman alone doesn't help

- A host port (`IP:port`) can have **only one listener**, whatever program asks for it. Docker, rootless Docker and Podman all publish ports by **listening on the host**.
- Rootless Docker publishes through RootlessKit on the host ([Docker docs: rootless tips](https://docs.docker.com/engine/security/rootless/tips/)). Rootless Podman does the same through pasta / `rootlessport` ([Podman docs: podman-network](https://docs.podman.io/en/latest/markdown/podman-network.1.html)).
- So two stacks that both publish `0.0.0.0:80` clash, **with or without Podman**.

### What does fix it: don't publish ports for the workflow stack

- **The workflow stack doesn't need host ports at all:**
  - the tests run **inside** the containers via `docker compose exec` (`test_runner.sh:55`, `:63`, `:88`);
  - the proxy healthcheck curls `dyflexis.dev.wodanbrothers.com` **from inside** the proxy container (`docker-compose.yml:135`);
  - the app hostnames are **network aliases** of `proxy` on the `dfs` network (`docker-compose.yml:149-154`), so containers reach each other without the host.
- **The fix:** the workflow adds its **own** override file that removes every `ports:` entry, using Compose's `!reset` tag ([Docker docs: merge, `!reset`](https://docs.docker.com/reference/compose-file/merge/#reset-value)):

```yaml
# written by the workflow, OUTSIDE the worktree (Claude can't edit it)
services:
  proxy:     { ports: !reset [] }
  db:        { ports: !reset [] }
  redis:     { ports: !reset [] }
  seaweedfs: { ports: !reset [] }
```

- `up_command` passes it as a second `--file`, after the worktree's `docker-compose.yml`.
- **Side bonus (once this follow-up is done):** no published ports means the **sysctl for ports < 1024** can be removed again.
- **Better:** generate the list from `docker compose config` (every service that has `ports`), so a new service with ports in the repo doesn't break it.

### Result once this follow-up is done (on top of option 2)

- **Your dev stack:** your root Docker, ports 80/443/3306/… as now. **Untouched, can stay up.**
- **Workflow stack:** `cw-docker`'s own daemon, own container names, own networks, **no host ports**.
- **Verify no longer has to stop your dev stack.** You don't have to pause the workflow either.

### Podman vs rootless Docker for the `cw-docker` daemon

This is a **separate choice** from the port question. Both give the same isolation (a non-root user that can't read `/home/joey`).

| | **Rootless Docker** | **Podman (rootless)** |
|---|---|---|
| Works with `docker compose` | Yes, native | Via Podman's Docker-compatible socket ([podman-system-service](https://docs.podman.io/en/latest/markdown/podman-system-service.1.html)); mostly works, edge cases differ |
| `docker.sock` mount for `proxy` / `proxy-companion` | Mount the rootless socket instead | Mount Podman's socket; nginx-proxy then reads Podman's Docker-API. **Not sure** it reads all events/labels the same |
| Daemon | A long-running `dockerd` per user | No daemon; a socket-activated API service |
| Same tool as your dev stack | Yes | No: a second tool to learn and debug |

- **My recommendation: stay with rootless Docker** for option 2. (This daemon choice **is** part of option 2; only the port fix is for later.) Same tool, fewer compose surprises, and the port fix above works the same way. Podman gives no extra benefit here.

### Not sure / to confirm in the follow-up plan

- **Subnet `172.31.0.0/16` twice.** I expect it's fine: rootless Docker creates its networks inside its own network namespace, so they don't overlap with the root daemon's bridges. **Confirm:** start both stacks and check `docker network inspect` on each.
- **`!reset` support.** Your Compose is v5.4.0; the docs don't state the minimum version. **Confirm:** `docker compose -f docker-compose.yml -f override.yml config` shows no `ports`.
- **`extra_hosts: host.docker.internal:host-gateway`** (`docker-compose.yml:224`). In rootless mode this points to the rootless namespace, not your real host. Only matters for Xdebug, which the workflow doesn't use. **Confirm** nothing in the tests calls it.
- **Not verified at all:** none of this has been run. It's based on reading the compose file, `test_runner.sh` and the docs above.
