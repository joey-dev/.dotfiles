# 5. Getting started

How to install, configure, and run the workflow. Each item says **what it does**.

**Tested:** the unit tests (116), the Nix build, the Q&A sandbox (via `tools/sandbox_shell.py`), and the dev shell environment with a test flake. **Not tested:** a full run on a real ticket.

---

## 5.1 Install (once per machine)

**What it does:** puts `claude-workflow`, `claude`, `bwrap`, `socat` on your `PATH`, and writes `~/.config/claude-workflow/config.json`.

1. `"ai"` is already in `hosts/roles.nix`.
2. Rebuild home-manager the way you normally do. The build **runs the tests**.

```sh
claude-workflow --help
```

---

## 5.2 First-time setup (once per machine)

### a. Log in to Claude Code on the host

**What it does:** your login is copied into each ticket's sandbox (one way). If a run says you're logged out, run `claude` on the host once and log in again.

```sh
claude    # log in, then exit
```

### b. Log in to the Atlassian MCP server

**What it does:** Intake fetches the Jira ticket through **`Atlassian-Rovo-MCP`**, the server in the repo's `.mcp.json` (`npx mcp-remote …`). Its login in `~/.mcp-auth` is copied into the sandbox.

1. Run `claude` **in the repo**, then `/mcp`.
2. Make sure `Atlassian-Rovo-MCP` shows **Connected**.

If the login ever expires, do this again on the host.

### c. (Optional) Create the knowledge base folder

**What it does:** Explore, Q&A, Plan, Review, Retro get it **read-only** at `~/kb`.

```sh
mkdir -p ~/notes/work-kb
```

---

## 5.3 First-time setup (once per repository)

### a. Set `verify_commands` — **required**

**What it does:** Verify runs these, and Implement is told to use them for test-first work. **An empty list makes Verify fail.**

### b. Set `flake_path` — recommended

**What it does:** Implement and Verify get the flake's dev shell environment (PHP, Composer, Node, …). It's loaded **once per run**.

### c. Install dependencies in your main checkout

**What it does:** `vendor/` and `node_modules/` from your **main checkout** are mounted read-only into the ticket worktree, if the lockfiles match.

- Keep your main checkout's dependencies installed and up to date.
- If a ticket changes `composer.lock` or `package-lock.json`, the next stage stops and tells you to run the install **in the worktree** on the host.

### d. Commit or stash local changes first

**What it does:** the worktree branches from your main checkout's `HEAD` at Explore. Uncommitted changes are **not** included (you get a warning).

### e. Where to put a per-repo config

There is **no automatic per-repo config file**:

- edit `roles/ai/configuration/workflows/config.json` and rebuild (applies to **all** repos), or
- keep a separate file and pass it with **`--config`**.

Example (**untested**, commands are placeholders):

```json
{
  "flake_path": "~/projects/my-repo",
  "verify_commands": [
    "vendor/bin/phpunit --testsuite unit",
    "npm run lint"
  ]
}
```

Keys you leave out keep their defaults.

---

## 5.4 Running it

```sh
cd ~/path/to/your/repo          # any folder inside the repo works
claude-workflow PROJ-123 [--from-stage STAGE | --only-stage STAGE] [--auto] [--config FILE]
```

| Parameter | What it does |
|---|---|
| `PROJ-123` | **Required.** Jira key. Case doesn't matter. Used for the state folder, worktree folder, and branch (`proj-123`). |
| `--from-stage STAGE` | Re-run `STAGE` **and every stage after it**. Earlier stages must be completed. |
| `--only-stage STAGE` | Re-run **only** `STAGE`, stop after you approve it. |
| `--auto` | Gates always "continue", the fix choice always "fix" (while rounds are left). Q&A, Retro and escalation stay interactive. |
| `--config FILE` | Use this JSON config instead of `~/.config/claude-workflow/config.json`. |

`STAGE` is one of: `intake`, `explore`, `qa`, `plan`, `implement`, `verify`, `review`, `retro`.

### Exit codes

| Code | Meaning |
|---|---|
| `0` | Finished, all stages already done, or `--only-stage` approved |
| `1` | Stage failed, aborted, out of fix rounds, bad ticket id, already running, config/git error |
| `130` | Ctrl-C |

### Common follow-ups

```sh
# Continue where it stopped (after a crash, failure, or abort)
claude-workflow PROJ-123

# Redo the plan, then continue
claude-workflow PROJ-123 --from-stage plan

# Implement again with the last verify/review feedback
claude-workflow PROJ-123 --from-stage implement
```

### Where to look

- **Artifacts:** `~/.local/state/claude-workflow/PROJ-123/`
- **Code changes:** `~/.local/state/claude-workflow/worktrees/PROJ-123/` (branch `proj-123`)
- **Blocked network calls:** `~/.local/state/claude-workflow/PROJ-123/proxy.log`
- **Feedback for Retro:** write `~/.local/state/claude-workflow/PROJ-123/feedback.md`

When done, the branch has **one commit**. Pushing and opening the MR is up to you.

### Testing a sandbox by hand

```sh
cd ~/path/to/your/repo
nix shell nixpkgs#python312 nixpkgs#socat nixpkgs#bubblewrap -c \
  python ~/.dotfiles/roles/ai/configuration/workflows/workflow/tools/sandbox_shell.py qa --interactive
```

Use `--copy-credentials -- claude` to start Claude inside. See the docstring at the top of the script for all options.

---

## 5.5 Config keys

File: `configuration/workflows/config.json`. Loader: `config.py:259`.

### Top level

| Key | Default | What it does |
|---|---|---|
| `repo_path` | git root of the current folder | Repository to work on |
| `worktree_base` | `<state_base>/worktrees` | Where worktrees are created |
| `state_base` | `~/.local/state/claude-workflow` | Where ticket state folders go |
| `kb_path` | `~/notes/work-kb` | Knowledge base, mounted read-only |
| `skills_base` | from `CLAUDE_WORKFLOW_SKILLS` | Folder with `shared/`, `intake/`, … skills |
| `flake_path` | `null` | Nix flake whose dev shell Implement and Verify use |
| `verify_commands` | `[]` | Shell commands for Verify; **must not be empty** |
| `shared_dependencies` | `vendor` + `composer.lock`, `node_modules` + `package-lock.json` | Folders mounted from main when lockfiles match |
| `max_plan_reviews` | `2` | Max plan review passes (≥ 1) |
| `max_escalations` | `3` | Max blocked-question rounds per stage (≥ 0) |
| `max_fix_rounds` | `3` | Max Verify/Review → Implement rounds (≥ 0) |
| `headless_timeout` | `3600` | Seconds per headless Claude call |
| `verify_timeout` | `1800` | Seconds per verify command |
| `commit_no_verify` | `true` | Skip git hooks for the final commit |

### Per stage (`stages.<name>.…`)

| Key | Values | What it does |
|---|---|---|
| `model` | e.g. `sonnet`, `opus` | Passed as `--model` |
| `thinking` | `low`, `medium`, `high`, `xhigh`, `max` | Passed as `--effort` |
| `repo_access` | `none`, `ro`, `rw` | How the worktree is mounted |
| `allow_network` | `true` / `false` | `false` = only Anthropic hosts via the proxy (Verify: no network at all) |
| `mcp_config` | path or `null` | MCP JSON file, mounted as `~/.claude/mcp.json` |
| `allowed_tools` | list of strings | Claude tools the stage may use |

---

## 5.6 Environment variables

| Variable | What it does |
|---|---|
| `XDG_STATE_HOME` | Base for `state_base` (default `~/.local/state`) |
| `XDG_CONFIG_HOME` | Base for the config file (default `~/.config`) |
| `CLAUDE_WORKFLOW_SKILLS` | Skills folder. **Set by the Nix wrapper** |

**Inside the sandbox**, only these host variables are kept: `HOME USER LOGNAME PATH SHELL LANG LC_ALL LC_CTYPE TERM COLORTERM TZ NIX_SSL_CERT_FILE SSL_CERT_FILE`. The flake's dev shell variables are added on top. Tokens and other secrets are **not** passed.

For no-network stages, the sandbox also sets `HTTPS_PROXY`, `HTTP_PROXY` and `NODE_USE_ENV_PROXY=1`, so traffic goes through the allowlist proxy.

---

## 5.7 Requirements checklist

- [ ] `ai` role rebuilt
- [ ] Logged in with `claude` on the host
- [ ] `Atlassian-Rovo-MCP` connected (`claude` in the repo → `/mcp`)
- [ ] `verify_commands` set
- [ ] `flake_path` set (if the repo needs a dev shell)
- [ ] Dependencies installed in your main checkout
- [ ] Local changes committed or stashed
