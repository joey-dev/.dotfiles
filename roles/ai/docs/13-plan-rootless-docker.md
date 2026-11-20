# 13. Rootless Docker for the workflow (option 2) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **Phase A (Tasks 1–2) and Task 7 run in the main session with the user** (`sudo`, a live Docker daemon, debugging). Only Phase B (Tasks 3–6) goes to subagents.

**Goal:** the workflow's compose stack runs in a **separate rootless Docker daemon** owned by the user `cw-docker`, so code Claude wrote can't reach `/home/joey`, and the workflow **refuses to use root Docker**.

**Architecture:**

- **NixOS:** a new `roles/ai/system.nix` creates `cw-docker`, its rootless daemon (socket in `/var/lib/cw-docker-sock/`), the sysctl for ports 80/443 and a shared worktree folder `/srv/claude-workflow/worktrees` with default ACLs.
- **Workflow:** two new global config keys, `docker-host` and `worktree-base`. Every `docker` call gets `DOCKER_HOST`. A generated compose override (outside the worktree) points the `docker.sock` mounts at the rootless socket.
- **Safety:** without a rootless `docker-host`, every Docker step stops with NEEDS_HUMAN. The plan-11 checks stay as extra layers.

**Tech Stack:** NixOS (`virtualisation.docker.rootless`, systemd-tmpfiles ACLs), Python 3.12, pytest, Docker Compose v5.

**Spec:** `12-docker-isolation-options.md` (option 2) and the research below. Background: `09-tests-and-docker.md`, `10-plan-tests-docker.md`.

All code paths are relative to `roles/ai/configuration/workflows/workflow/` unless they start with `roles/` or `hosts/`.

---

## Research results (step 1, 2026-11-19)

Three read-only research agents. **Verified** = read in source, docs or the repo. **Guess** = to confirm in the spike (Task 2).

### NixOS (verified in the module source, `nixos/modules/virtualisation/docker-rootless.nix`)

- `virtualisation.docker.rootless` defines **one** `systemd.user.services.docker` for **every** user (`ConditionUser = "!root"`, lines 75–84). We must limit it with `lib.mkForce "cw-docker"`.
- `setSocketVariable = true` sets `DOCKER_HOST` for **all** users. **Must stay `false`**, or the user's own root-Docker dev stack breaks.
- It coexists with `virtualisation.docker.enable = true` (root daemon).
- `dockerd-rootless.sh:62-69` refuses to run without `$HOME`, so `cw-docker` is an `isNormalUser` with a home. `linger = true` starts its user manager at boot.
- `daemon.settings.hosts` sets the socket path. Rootlesskit copies up `/run`, so the socket goes **outside `/run`**: `/var/lib/cw-docker-sock/docker.sock`.
- This host: cgroup v2 with delegation, user namespaces on, kernel 6.18 (native overlay OK), `ip_unprivileged_port_start = 1024` (so 80/443 need the sysctl).


### Compose file (verified in `~/Code/Work/dyflexis-monorepo`)

- **`docker.sock` is hard-coded** (`docker-compose.yml:67`) and mounted by `proxy` (`:141-143`) and `proxy-companion` (`:166-168`).
- **Containers write into the worktree as uid 1000:** `dyflexis-composer` as `${HOST_UID}:${HOST_GID}` (`:371`), `legacy-web-debug`, `lighttpd`, `object-storage-fixture`, and `test_runner.sh:5` (`--user ${UID:-1000}:${GID:-1000}`; `#!/bin/sh`).
- **Rootless uid mapping** ([Docker docs](https://docs.docker.com/engine/security/rootless/)): container root = `cw-docker`; container uid `N ≥ 1` = host uid `subuid-start + N − 1`.
- **Every bind source is inside the worktree**, except the socket (and `~/.npmrc`, see 09 Known limits).
- **Images** come from `registry.gitlab.com/dyflexis/...` and `gitlab.com/dyflexis/dependency_proxy/...`. Several are built locally.
- **Guess:** pull/build credentials come from the **client** (`~/.docker/config.json` of the user running `docker`), so the user's existing login works and `cw-docker` needs none.

### Workflow code (verified)

- `DOCKER_HOST` is needed in **two** places: `compose_env` (`claude_workflow/docker_stack.py:235`) and `_run_container` (`claude_workflow/runners.py:208-226`, uses `env=None` today).
- **Worktree base** is `~/.local/state/claude-workflow/worktrees` (`claude_workflow/config.py:230`), with **no config key**. Plan 12 said `~/Code/Worktrees`: that was wrong.
- The code never sets `HOST_UID` / `HOST_GID`.
- The bwrap sandbox binds no Docker socket at all (`claude_workflow/sandbox.py:17-29`) and runs `--clearenv`.

---

## Decisions (defaults chosen by me; the user confirms them by approving this plan)

1. **Ids:** user `cw-docker`, uid **2001**, group `cw-docker` gid **2001**, subuid/subgid range **200000–265535**. So **container uid/gid 1000 = host 200999**.
2. **Socket:** `/var/lib/cw-docker-sock/docker.sock`, folder `0750 cw-docker:cw-docker`. The user is added to group `cw-docker`.
3. **Worktree base:** `/srv/claude-workflow/worktrees`, owner `joey`, group `cw-docker`, mode `2770`, with default ACLs for `joey`, group `cw-docker` and host uid/gid **200999** (container 1000). With a default ACL the umask is ignored, so new files get the ACL rights (limited by the mode the program asks for).
4. **Containers keep their own uids.** No `user: 0:0` override. **Why:** `test_runner.sh` is protected and hard-codes `--user ${UID}`, so the ACLs must make uid 1000 work anyway.
5. **Root Docker is refused.** If `docker-compose` is configured but `docker-host` is not set, or points at the root socket, Docker steps raise `HostStop` (Verify → NEEDS_HUMAN).
6. **Ports:** the rootless stack still publishes 80/443/3306/…. **Verify does not stop the dev stack itself.** If `up` fails with "address already in use", the FAIL output says: stop your dev stack. (Running both at once is the follow-up in doc 12's last section, **not part of this plan**.)
7. **The override file** lives at `<state_base>/compose/<project-name>.override.json`, outside the worktree and outside every sandbox bind.

## Global Constraints

- **Never** set `virtualisation.docker.rootless.setSocketVariable = true`.
- **Never** give `cw-docker` a subuid range that contains uid 1000 (the user's uid).
- Keys are kebab-case, as in plan 11.
- `docker-host` must be a `unix://` URI with an absolute path.
- No change to files in the Dyflexis repo. Everything goes through config and the generated override.
- `nixos-rebuild switch` is run **by the user**, never by an agent.

## Review Focus

1. **`docker-host` that still reaches root Docker** (`unix:///var/run/docker.sock`, `unix:///run/docker.sock`, a symlink to them) → must be refused. Test in Task 4.
2. **An inherited `DOCKER_HOST`** in the user's shell → the configured value must win; with no `docker-host` configured, an inherited one must **not** count as rootless. Test in Task 4.
3. **A compose file without socket mounts** → the override has no services and `up` still works. Test in Task 5.
4. **`DOCKER_HOST` leaking into the bwrap sandbox** → must not happen (`--clearenv`). Test in Task 4.
5. **A worktree base inside `$HOME`** while `docker-host` is set → `cw-docker` can't read it; stop early with a clear message instead of a vague mount error. Test in Task 4.

---

## Phase A — NixOS (main session, with the user)

### Task 1: NixOS: `cw-docker` user, rootless daemon, shared worktree folder

**Files:**
- Create: `roles/ai/system.nix`
- Modify: `hosts/work/configuration.nix` (enable the option)

**Interfaces:**
- Produces: option `roles.ai.dockerSandbox.enable` (default `false`); socket `/var/lib/cw-docker-sock/docker.sock`; folder `/srv/claude-workflow/worktrees`.

- [ ] **Step 1: Write `roles/ai/system.nix`.** It declares `options.roles.ai.dockerSandbox.enable = lib.mkEnableOption "...";` (`roles/system.nix` only declares `roles.<name>.enable`) and sets, under `lib.mkIf (config.roles.ai.enable && config.roles.ai.dockerSandbox.enable)`. The ACL lines are **untested** syntax; the build won't check them, the spike (Task 2) does:
  - `virtualisation.docker.rootless = { enable = true; setSocketVariable = false; daemon.settings.hosts = [ "unix:///var/lib/cw-docker-sock/docker.sock" ]; }`;
  - `systemd.user.services.docker.unitConfig.ConditionUser = lib.mkForce "cw-docker";`
  - `users.groups.cw-docker.gid = 2001;`
  - `users.users.cw-docker = { isNormalUser = true; uid = 2001; group = "cw-docker"; linger = true; subUidRanges = [{ startUid = 200000; count = 65536; }]; subGidRanges = [{ startGid = 200000; count = 65536; }]; autoSubUidGidRange = false; };`
  - `users.users.${username}.extraGroups = [ "cw-docker" ];`
  - `boot.kernel.sysctl."net.ipv4.ip_unprivileged_port_start" = 80;`
  - `systemd.tmpfiles.rules`:
    - `d /var/lib/cw-docker-sock 0750 cw-docker cw-docker -`
    - `d /srv/claude-workflow 0750 ${username} cw-docker -`
    - `d /srv/claude-workflow/worktrees 2770 ${username} cw-docker -`
    - `A+ /srv/claude-workflow/worktrees - - - - d:u:${username}:rwx,d:g:cw-docker:rwx,d:u:200999:rwx,d:g:200999:rwx,u:${username}:rwx,g:cw-docker:rwx,u:200999:rwx,g:200999:rwx,d:m::rwx,m::rwx`
  - `/srv/claude-workflow` also needs traverse for uid 200999: `A+ /srv/claude-workflow - - - - u:200999:x,g:200999:x`.

- [ ] **Step 2: Enable it** in `hosts/work/configuration.nix`: `roles.ai.dockerSandbox.enable = true;`

- [ ] **Step 3: Build without switching**

Run: `nixos-rebuild build --flake .#work` (from the worktree)
Expected: builds without errors. Then show the user `git diff`.

- [ ] **Step 4: The user switches** — `sudo nixos-rebuild switch --flake .#work`, then logs out and in (new group).

- [ ] **Step 5: Commit**

```bash
git add roles/ai/system.nix hosts/work/configuration.nix
git commit -m "ai: rootless Docker daemon for the workflow (cw-docker)"
```

### Task 2: Spike — prove the isolation by hand (go / no-go gate)

No code. Run each check **as the user**, with `export DOCKER_HOST=unix:///var/lib/cw-docker-sock/docker.sock`. Write the results into a "Spike results" section at the end of this file.

- [ ] **Daemon runs and is rootless:** `systemctl --user -M cw-docker@ status docker` is active; `docker info` shows `rootless` in Security Options and Storage Driver `overlay2`.
- [ ] **The user's own daemon is unchanged:** `env -u DOCKER_HOST docker ps` lists the dev stack; `systemctl --user status docker` says the unit's condition failed (no rootless daemon for the user).
- [ ] **Home is unreachable:** `docker run --rm -v /home/joey:/h alpine ls /h` fails (permission denied, or an empty/error mount).
- [ ] **uid 1000 can write the worktree base:** `mkdir /srv/claude-workflow/worktrees/spike` then `docker run --rm -u 1000:1000 -v /srv/claude-workflow/worktrees/spike:/w alpine sh -c 'mkdir -p /w/a/b && echo x > /w/a/b/f'` succeeds.
- [ ] **The user can edit and delete what the container wrote:** `echo y >> /srv/claude-workflow/worktrees/spike/a/b/f && rm -rf /srv/claude-workflow/worktrees/spike` succeeds.
- [ ] **Container root (= `cw-docker`) can write too:** the same `docker run` without `-u` succeeds.
- [ ] **Other container groups:** several services run as `$HOST_UID:www-data`, `:lighttpd` or `:node`, so container gid ≠ 1000. `docker run --rm -u 1000:33 ...` (same write test) succeeds. Also try an unrelated uid, `-u 33:33`, reading a file in the worktree; record what happens (no ACL covers host uid 200032).
- [ ] **`HOST_GID` is unset:** the monorepo `.env` has `HOST_UID=1000` but no `HOST_GID`, so `dyflexis-composer` gets `user: "1000:"`. In a scratch worktree, `docker compose config dyflexis-composer` shows what Compose makes of it. If it breaks, `compose_env` sets `HOST_GID=1000` (Task 4).
- [ ] **Registry with the user's login:** `docker pull registry.gitlab.com/dyflexis/<one image from the compose file>` and one `gitlab.com/dyflexis/dependency_proxy/...` image succeed.
- [ ] **Port 80:** with the dev stack **down**, `docker run --rm -p 80:80 nginx` binds. With it **up**, it fails with "address already in use".
- [ ] **Sandbox can't see the socket:** in a `sandbox_shell.py` shell, `ls /var/lib/cw-docker-sock` fails.

**If a check fails:** stop and decide with the user. Known fallbacks:
- write checks fail → a `fix-perms` step (throwaway container as root: `chmod -R g+rwX` on paths not owned by `nobody`) after each stack run, added as a task before Task 7;
- `daemon.settings.hosts` / socket access fails → use `/run/user/2001` with a systemd socket proxy;
- the whole approach fails → the VM variant from doc 12.

---

## Phase B — workflow code (subagent-driven)

### Task 3: Config keys `docker-host` and `worktree-base`

**Files:**
- Modify: `claude_workflow/config.py` (`WorkflowConfig` ~line 115, `load_config` ~line 583)
- Modify: `../config/config.schema.json` (top-level properties)
- Modify: `../config/global.config.json`
- Test: `tests/test_config.py`

**Interfaces:**
- Produces: `WorkflowConfig.docker_host: str | None = None` and `WorkflowConfig.worktree_base: Path` now settable.

- [ ] **Step 1: Write the failing tests**

```python
def test_docker_host_and_worktree_base_from_global(tmp_path):
    # global sets "docker-host": "unix:///var/lib/cw-docker-sock/docker.sock",
    #             "worktree-base": "/srv/claude-workflow/worktrees"
    cfg = load_config(repo, config_dir)
    assert cfg.docker_host == "unix:///var/lib/cw-docker-sock/docker.sock"
    assert cfg.worktree_base == Path("/srv/claude-workflow/worktrees")

def test_docker_host_defaults_to_none_and_worktree_base_to_state(tmp_path):
    cfg = load_config(repo, config_dir)  # neither key set
    assert cfg.docker_host is None
    assert cfg.worktree_base == cfg.state_base / "worktrees"

def test_worktree_base_expands_tilde(tmp_path): ...  # "~/wt" -> Path.home() / "wt"

def test_docker_host_must_be_unix_uri(tmp_path):
    # "tcp://1.2.3.4:2375" and "unix://relative/x" -> check_config returns an error naming docker-host
```

- [ ] **Step 2: Run them, expect FAIL** — `pytest tests/test_config.py -k "docker_host or worktree_base" -v`

- [ ] **Step 3: Implement**
  - schema: `"docker-host": {"type": ["string", "null"], "pattern": "^unix:///.+", "description": "..."}`, `"worktree-base": {"type": "string", "minLength": 1, "description": "..."}`;
  - `load_config`: `docker_host=raw.get("docker-host")`, `worktree_base=_expand_path(raw["worktree-base"]) if "worktree-base" in raw else base.worktree_base`;
  - `global.config.json`: both keys with the Decision 2/3 values.
  - **Known effect, no code:** a ticket started before this change has its worktree under the old base, so `pipeline.py:207-210` refuses to resume it ("outside the configured ticket worktree path"). That's correct: such a ticket restarts. Mention it in 08.

- [ ] **Step 4: Run the whole suite, expect PASS** — `pytest -q`

- [ ] **Step 5: Commit** — `git commit -m "ai: config keys docker-host and worktree-base"`

### Task 4: `DOCKER_HOST` everywhere, and refuse root Docker

**Files:**
- Modify: `claude_workflow/docker_stack.py` (`compose_env`, new `docker_env`, new `require_rootless`)
- Modify: `claude_workflow/runners.py` (`_ensure_stack`, `_run_host`, `_run_container`)
- Test: `tests/test_docker_stack.py`, `tests/test_runners.py`, `tests/test_sandbox.py`

**Interfaces:**
- Consumes: `WorkflowConfig.docker_host`, `WorkflowConfig.worktree_base` (Task 3).
- Produces:
  - `docker_env(docker_host: str) -> dict[str, str]` — `os.environ` copy with `DOCKER_HOST` set (overrides an inherited one).
  - `compose_env(cfg: DockerConfig, worktree: Path, repo: Path, docker_host: str, override: Path | None = None) -> dict[str, str]` — builds on `docker_env`. With `override`, `COMPOSE_FILE` is `"<worktree>/docker-compose.yml:<override>"` (Task 5 passes it).
  - `require_rootless(docker_host: str | None, worktree_base: Path) -> str` — returns `docker_host`, or raises `ValueError` with a message for the human.
  - `ROOT_DOCKER_SOCKETS = (Path("/var/run/docker.sock"), Path("/run/docker.sock"))`.

- [ ] **Step 1: Write the failing tests**

```python
def test_require_rootless_refuses_missing_host():
    with pytest.raises(ValueError, match="docker-host"):
        require_rootless(None, Path("/srv/w"))

@pytest.mark.parametrize("uri", ["unix:///var/run/docker.sock", "unix:///run/docker.sock"])
def test_require_rootless_refuses_root_socket(uri):
    with pytest.raises(ValueError, match="root Docker"):
        require_rootless(uri, Path("/srv/w"))

def test_require_rootless_refuses_symlink_to_root_socket(tmp_path):
    # tmp_path/s -> /var/run/docker.sock ; resolve() catches it
    ...

def test_require_rootless_refuses_worktree_base_in_home():
    with pytest.raises(ValueError, match="cw-docker can't read"):
        require_rootless("unix:///var/lib/cw-docker-sock/docker.sock", Path.home() / "wt")

def test_docker_env_overrides_inherited(monkeypatch):
    monkeypatch.setenv("DOCKER_HOST", "unix:///var/run/docker.sock")
    assert docker_env("unix:///x/d.sock")["DOCKER_HOST"] == "unix:///x/d.sock"

def test_compose_env_sets_docker_host_and_override(tmp_path): ...
    # COMPOSE_FILE == f"{wt}/docker-compose.yml:{override}"

# test_runners.py
def test_container_command_passes_docker_host(...)  # run_command got env["DOCKER_HOST"]
def test_host_command_with_compose_config_stops_without_docker_host(...)  # HostStop
def test_compose_up_stops_without_docker_host(...)  # HostStop, `up` never called

# test_sandbox.py
def test_bwrap_does_not_pass_docker_host(monkeypatch): ...  # DOCKER_HOST set on host, absent from argv
```

- [ ] **Step 2: Run them, expect FAIL** — `pytest tests/test_docker_stack.py tests/test_runners.py tests/test_sandbox.py -v`

- [ ] **Step 3: Implement**
  - `require_rootless`: refuse `None`, a non-`unix://` URI, a path whose `Path(p).resolve()` equals any `ROOT_DOCKER_SOCKETS` entry resolved, and a `worktree_base` that is inside `Path.home()`.
  - runners: a helper `_docker_host(ctx) -> str` calls `require_rootless(ctx.config.docker_host, ctx.config.worktree_base)` and turns `ValueError` into `HostStop`. Call it in `_ensure_stack` (before the guard), in `_run_host` when `ctx.config.docker` is set, and always in `_run_container`.
  - `_run_container` passes `env=docker_env(host)` instead of `None`.
  - Update existing tests that call `compose_env` / build a `WorkflowConfig` with Docker to set `docker_host` and a `worktree_base` outside home.

- [ ] **Step 4: Run the whole suite, expect PASS** — `pytest -q`

- [ ] **Step 5: Commit** — `git commit -m "ai: run Docker only through the rootless daemon"`

### Task 5: Compose override for the `docker.sock` mounts, and the port hint

**Files:**
- Modify: `claude_workflow/docker_stack.py` (`socket_override`, `compose_model`, `write_override`, `up_command`, `port_hint`)
- Modify: `claude_workflow/runners.py` (`_ensure_stack`, `_run_host`)
- Test: `tests/test_docker_stack.py`, `tests/test_runners.py`

**Interfaces:**
- Consumes: `docker_env`, `compose_env(..., override=)` (Task 4).
- Produces:
  - `socket_override(model: dict[str, Any], socket_path: str) -> dict[str, Any]` — pure.
  - `compose_model(cfg: DockerConfig, worktree: Path, repo: Path, docker_host: str) -> dict[str, Any]` — runs `docker compose ... config --format json` (same `--project-name/--project-directory/--file/--env-file/--profile` as `up_command`), raises `ValueError` on a non-zero exit or bad JSON.
  - `override_path(state_base: Path, cfg: DockerConfig) -> Path` = `state_base / "compose" / f"{cfg.project_name}.override.json"`.
  - `up_command(cfg, worktree, repo, override: Path | None = None) -> list[str]` — adds `--file <override>` right after the compose file.
  - `port_hint(output: str) -> str` — adds one line when the output says `address already in use`.

- [ ] **Step 1: Write the failing tests**

```python
MODEL = {"services": {
    "proxy": {"volumes": [
        {"type": "bind", "source": "/var/run/docker.sock", "target": "/tmp/docker.sock", "read_only": True},
        {"type": "bind", "source": "/w/nginx-proxy/certs", "target": "/etc/nginx/certs"}]},
    "db": {"volumes": [{"type": "volume", "source": "db", "target": "/var/lib/mysql"}]},
}}

def test_socket_override_repoints_only_socket_mounts():
    assert socket_override(MODEL, "/var/lib/cw-docker-sock/docker.sock") == {"services": {
        "proxy": {"volumes": [{"type": "bind", "source": "/var/lib/cw-docker-sock/docker.sock",
                               "target": "/tmp/docker.sock", "read_only": True}]}}}

def test_socket_override_also_matches_run_docker_sock(): ...   # source "/run/docker.sock"
def test_socket_override_without_socket_mounts_is_empty():
    assert socket_override({"services": {"db": {}}}, "/s") == {"services": {}}

def test_up_command_adds_override_file(tmp_path):
    argv = up_command(cfg, wt, repo, override=tmp_path / "o.json")
    i = argv.index(str(wt / "docker-compose.yml"))
    assert argv[i + 1 : i + 3] == ["--file", str(tmp_path / "o.json")]

def test_override_path_is_outside_worktree_and_sandbox(...)  # under state_base/"compose"

def test_port_hint():
    assert "stop your dev stack" in port_hint("Bind for 0.0.0.0:80 failed: port is already allocated / address already in use")
    assert port_hint("other error") == "other error"

# test_runners.py
def test_compose_up_writes_override_and_uses_it(...)  # override file exists, `up` argv has it
def test_compose_up_config_failure_is_host_stop(...)  # compose_model raises -> HostStop
```

- [ ] **Step 2: Run them, expect FAIL** — `pytest tests/test_docker_stack.py tests/test_runners.py -v`

- [ ] **Step 3: Implement**
  - Socket sources to replace: `{"/var/run/docker.sock", "/run/docker.sock"}`. Keep `target` and `read_only`; output only the socket volumes per service. Compose merges `volumes` **by target**, so the override replaces just that mount ([merge rules](https://docs.docker.com/reference/compose-file/merge/)).
  - `_ensure_stack` order: `_docker_host` → guard → `prepare_worktree` → `compose_model` → `write_override` (JSON, `mkdir(parents=True)`) → `up_command(..., override=)` with `compose_env(..., override=)`. Store the override path in `StackState.override: Path | None` so `_run_host` passes the same file to `compose_env`.
  - On `up` FAIL, return `port_hint(output)` as the output.

- [ ] **Step 4: Run the whole suite, expect PASS** — `pytest -q`; also `ruff check` and the type checker the repo uses (see `pyproject.toml`).

- [ ] **Step 5: Commit** — `git commit -m "ai: compose override points docker.sock mounts at the rootless daemon"`

### Task 6: Docs and stale comments

**Files:**
- Modify: `claude_workflow/docker_stack.py:1-7`, `:145-146` (docstrings say "root Docker"); `claude_workflow/runners.py:10` ("Docker access is host root")
- Modify: `../config/config.schema.json` — `project-name` description ("so a worktree takes over its containers" is no longer true: separate daemon)
- Modify: `roles/ai/docs/09-tests-and-docker.md`, `12-docker-isolation-options.md` (option 2 = built; fix "`~/Code/Worktrees`" and the registry-login line), `08-next-session.md` (status row for plan 13), `05-getting-started.md` (one-time setup: `nixos-rebuild`, re-login for the group)

- [ ] **Step 1: Make the edits.** Keep the style: short bullets, bold key terms.
- [ ] **Step 2: Run `pytest -q`** (schema change) — PASS.
- [ ] **Step 3: Commit** — `git commit -m "ai/docs: rootless Docker (plan 13)"`

---

## Task 7: First real run (main session, with the user)

Plan 10's Task 6 checks, now against the rootless daemon. Dev stack **down** first.

- [ ] `claude-workflow config check` in the monorepo: no errors.
- [ ] A test ticket's worktree lands in `/srv/claude-workflow/worktrees/<ticket>`.
- [ ] Verify starts the stack: `docker --host unix:///var/lib/cw-docker-sock/docker.sock compose ls` shows it; `env -u DOCKER_HOST docker ps` does **not**.
- [ ] `proxy` healthy; `proxy-companion` logs show no socket errors.
- [ ] `tests:integration` and `tests:api` run and report PASS/FAIL (not a permission error).
- [ ] **Symlink attack fails:** in a scratch worktree, replace `legacy/pub` with a symlink to `/home/joey`, start the stack **by hand** (bypassing the guard) → the mount fails or shows nothing.
- [ ] After the run, the user can `git status`, edit and delete files in the worktree, and `git worktree remove` works.
- [ ] **Empty override:** Compose accepts an override with `{"services": {}}` (a model without socket mounts); record what happens.
- [ ] **Restrictive modes:** files a container writes with mode 0600/0700 can still be edited and removed by the user, and `git worktree remove` works.
- [ ] **Git inside containers:** the worktree `.git` file points into `/home/joey`, which `cw-docker` cannot read. Run `git status` in a container and record what happens.
- [ ] Without `docker-host` in the config → Verify ends with NEEDS_HUMAN, and the message names `docker-host`.
- [ ] Write the results into "Spike results" / 08, and update 08's status table.

---

## Spike results

### Task 2 (2026-11-20, after reboot)

**Fix needed first:** the socket was `2001:200130`, so the user got "permission denied". dockerd sets the socket group to `docker` by default; inside the user namespace that is the host's root-docker gid 131 → subgid **200130**. Fixed with `daemon.settings.group = "0"` in `roles/ai/system.nix` (gid 0 inside = `cw-docker` 2001). After switch + daemon restart the socket is `2001:2001`.

| Check | Result |
|---|---|
| Daemon rootless | **Pass.** Security options `rootless`, `cgroupns`; Docker 29.9.3. Storage driver is `overlayfs` (containerd snapshotter), not `overlay2`: fine |
| User's own daemon unchanged | **Pass.** `env -u DOCKER_HOST docker ps` reaches root Docker; the user's `docker.service` is skipped (`ConditionUser=cw-docker was not met`) |
| Home unreachable | **Pass.** `-v /home/joey:/h` → `ls: can't open '/h': Permission denied` |
| uid 1000 writes worktree base | **Pass** with `-u 1000:1000`, `-u 1000:100` and `-u 1000:33` |
| Container root writes | **Pass** (files owned `2001:2001`) |
| User edits + deletes container files | **Pass.** Files are `200999:2001` (setgid dir), `rw` for the user via ACL; `rm -rf` works |
| Unrelated uid `-u 33:33` | **Cannot** read or write (no ACL for host 200032). Risk: a process that drops to `www-data` inside a container (nginx/php-fpm workers) can't read the worktree. Check in Task 7 |
| `HOST_GID` | The user set `HOST_GID=100` in `.env` (gid of `users`). `docker compose config` gives `user: 1000:100`. No `compose_env` change needed |
| Registry with the user's login | **Pass.** Pulled from `registry.gitlab.com/dyflexis/...` and `gitlab.com/dyflexis/dependency_proxy/...`; `cw-docker` needs no login |
| Port 80, dev stack down | **Pass.** Binds on 0.0.0.0:80 and [::]:80 |
| Port 80 in use | **Not run** (the agent's test listener on :80 was blocked). Check by hand in Task 7 |
| Sandbox can't see the socket | **Pass.** In `sandbox_shell.py explore`: no `/var/lib/cw-docker-sock`, no `/srv`, `DOCKER_HOST` unset |

**Verdict: go** for Phase B.

(Task 7 results follow here.)
