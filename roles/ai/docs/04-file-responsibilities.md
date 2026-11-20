# 4. What each file is responsible for

One line of **responsibility** per file.

Paths are relative to `roles/ai/`.

---

## 4.1 Nix and setup

| File | Responsible for |
|---|---|
| `ai.nix` | **Installs everything** when `roles.ai.enable` is on: `claude-code`, `codex`, `jq`, `libnotify`, `bubblewrap`, and the **`claude-workflow` Python app**. Links `configuration/claude/` into `~/.claude/` and the workflow config folder to `~/.config/claude-workflow/`. |

**Details on the Nix package:**

- Built with `buildPythonApplication` from `configuration/workflows/workflow/`.
- **Runs the test suite during the build** (`pytestCheckHook`).
- Copies `skills/` into the package, and the wrapper sets **`CLAUDE_WORKFLOW_SKILLS`** to them.
- The wrapper puts `bwrap`, `git`, `notify-send`, `claude`, `socat` on `PATH`.

---

## 4.2 General Claude Code config

| File | Responsible for |
|---|---|
| `configuration/claude/CLAUDE.md` | Your **personal instructions**. Also mounted read-only in every workflow sandbox. |
| `configuration/claude/settings.json` | Your **global Claude Code settings**. The workflow uses a copy **without hooks** inside the sandbox. |

---

## 4.3 Workflow config

Folder: `configuration/workflows/config/`.

| File | Responsible for |
|---|---|
| `global.config.json` | **Global settings**: `kb-path`, `flake-path`, the limits (`max-*`, `headless-timeout`, `commit-no-verify`) and `stages` (model, thinking, access, network, tools). |
| `repository/<repo-name>.config.json` | **Per-repo settings**: `commands`, `verify`, `docker-compose`, `shared-dependencies`, and any override of a global key. `<repo-name>` is the folder name of the repo root. |
| `config.schema.json` | **The schema** for both files. Neovim uses it live through `$schema`. It also states the merge rule. |
| `example.config.json` | **A copy-paste example**: the repo file plus the global keys in one file. |
| `full-configs/<repo-name>.config.json` | **Generated, gitignored**: the merged result of `claude-workflow config render`. A read-only view; the workflow never reads it. |

**Merge rule:** the repo file overrides the global file. Objects merge per key. Arrays and plain values are replaced.

---

## 4.4 Python package: `configuration/workflows/workflow/`

### Project files

| File | Responsible for |
|---|---|
| `pyproject.toml` | Package metadata, the **`claude-workflow` entry point**, Python ≥ 3.12, no runtime dependencies, tool settings. |
| `tools/sandbox_shell.py` | **Debug helper**: opens `bash` (or any command) in the exact sandbox of a stage. Not installed. |

### `claude_workflow/` (core)

| File | Responsible for |
|---|---|
| `cli.py` | **Command line**: parse arguments, load config, find the git root, run the pipeline. |
| `config.py` | **Settings model**: stage names and order, defaults, loading of global + repo config, schema validation (errors name the source file), merge, `config check` / `config render`. |
| `commands.py` | **Named commands**: the `Command` / `Parameter` / `VerifyEntry` models, parsing, and `render` (shell-quoted word by word, full-match patterns, no value word starting with `-` or holding `..` when it comes from `tests.txt`). |
| `runners.py` | **Running a command** by `run-in`: `sandbox` (bwrap, no network), `host` (guard first, base-commit copy of the script), `container` (`docker exec`). |
| `catalogue.py` | **Command list for prompts**: name, description, `run-in` and parameters for Plan, Implement and Review. Raw host/container command text is never shown. |
| `pipeline.py` | **Orchestration**: lock, start stage, stage order, gates, fix loop, escalation, final commit. |
| `state.py` | **Checkpoint**: `TicketState` and crash-safe save/load of `state.json`. |
| `claude_runner.py` | **Starting Claude**: CLI flags, skills as system prompt, settings file, proxy, timeout. |
| `sandbox.py` | **Isolation**: fake `$HOME`, safe one-way login copy, hook-free settings, in-sandbox paths, the `bwrap` command. |
| `env.py` | **Environment**: allowlisted host variables plus the flake's dev shell variables. |
| `deps.py` | **Shared dependencies**: mount `vendor/` / `node_modules/` from main when the lockfiles match. |
| `net_proxy.py` | **Network allowlist**: `CONNECT` proxy for `api.anthropic.com` and `platform.claude.com`, with a log. |
| `git_host.py` | **Git on the host**: repo root, worktree, diff, changed files, ignored/touched paths, commit. Never pushes. |
| `tests_file.py` | **`tests.txt` parser**: one line is `<command> [key=value ...]`. The command must exist, and every key needs a `pattern` and a full match. `render` checks it all again. |
| `docker_stack.py` | **Host-side Docker**: the guard (protected files must equal base), worktree prep (`host-copies` with optional `include` filter, `create-dirs`), compose env and `up` command (with the configured `services`), base-commit copy of a host script, command execution. Claude never calls it. |

### `claude_workflow/stages/`

| File | Responsible for |
|---|---|
| `__init__.py` | `STAGE_REGISTRY`: which class runs which stage. |
| `base.py` | **Shared stage code**: ticket worktree, sandbox from config, verdict parsing, blocker check, artifact helpers, headless run. |
| `intake.py` | Stage 1: fetch the ticket via the repo's Atlassian MCP server → `01-ticket.md`. |
| `explore.py` | Stage 2: create the worktree, explore read-only → `02-findings.md`. |
| `qa.py` | Stage 3: interactive Q&A with a resumable session → `03-qa.md`. |
| `plan.py` | Stage 4: test-first plan, review/revise loop → `04-plan.md`, `04-plan-review.md`. |
| `implement.py` | Stage 5: test-first implementation, fix rounds → code + `05-implement.md`. |
| `verify.py` | Stage 6: the `verify` entries, then the `tests.txt` lines, each through `render` and the runners → `06-verify.md`. Output sits in fences longer than any backtick run inside it. |
| `review.py` | Stage 7: `diff.patch`, two review lenses → `07-review*.md`. |
| `retro.py` | Stage 8: interactive human check and proposals → `08-retro.md`. |

### `skills/`

One `SKILL.md` per stage, plus `shared/`. Each stage gets **`shared` + its own** as a system prompt. Retro also gets all of them as files at `~/skills`.

### `tests/`

| File | Tests |
|---|---|
| `test_config.py` | Global + repo loading, merge, validation, error source files. |
| `test_cli_config.py` | `config check` and `config render`. |
| `test_commands.py` | Command parsing, durations, `host_script`. |
| `test_render.py` | Rendering, quoting, patterns, `-` and `..` rules for `tests.txt` values. |
| `test_runners.py` | Sandbox, host and container runners. |
| `test_state.py` | Atomic save/load, resume stage. |
| `test_pipeline.py` | Full run, resume, escalation cap, plan loop, gates, blocker fixes, verdict wiring, test-first plan. |
| `test_fix_loop.py` | Fix loop, fix choice, feedback handling, Implement prompt, Verify NEEDS_FIX and timeouts. |
| `test_ticket_worktree.py` | Worktree at Explore, fixed base, dirty warning, dependency mounts, home mounts. |
| `test_ticket_key.py` | Lower-case ticket keys. |
| `test_deps.py` | The 4 shared-dependency rules. |
| `test_env.py` | Env allowlist, dev shell capture (banner, invalid names), `PATH` merge, cache, failure. |
| `test_verdict.py` | Verdict parsing with markdown. |
| `test_intake.py` | Repo `.mcp.json` for MCP stages, default tools, failure hint, safe `~/.mcp-auth` copy. |
| `test_claude_runner.py` | CLI flags, session flags, system prompt, timeout. |
| `test_sandbox.py` | bwrap mounts, no skills mount, clean env, terminal, settings, home mounts, safe login copy (symlink attacks). |
| `test_net_proxy.py` | Allow/deny, tunnel, default hosts, log, log symlink attack. |
| `test_git_host.py` | Worktree, diff, commit, repo root, changed files, ignored/touched paths, `--no-verify`. |
| `test_tests_file.py` | `tests.txt` parsing and validation. |
| `test_docker_stack.py` | Guard, worktree prep (include filter), compose env/command (services), base script copy. |
| `test_workflow_regressions.py` | Older specific bugs. |

---

## 4.5 Files created at runtime (not in the repo)

| Path | Created by | Contains |
|---|---|---|
| `~/.local/state/claude-workflow/<TICKET>/state.json` | `state.py` | Checkpoint |
| `…/<TICKET>/.lock` | `pipeline.py` | Lock for one run per ticket |
| `…/<TICKET>/home/` | `sandbox.py` | Fake `$HOME` with your login and Claude session data |
| `…/<TICKET>/proxy.log` | `net_proxy.py` | `ALLOW` / `DENY` / `REJECT` per connection |
| `…/<TICKET>/01-ticket.md` … `08-retro.md` | stages | Stage artifacts |
| `…/<TICKET>/blocked-questions.md` | Claude (Plan/Implement) | Questions; deleted after escalation |
| `…/<TICKET>/tests.txt` | Claude (Plan writes it; Implement and Review may add lines) | The ticket's test list (command names with parameters), read by Verify |
| `~/.local/state/claude-workflow/.cache/<TICKET>/<stage>/` | `base.py` (`stage_cache_dir`) | Persistent `$TMPDIR` (phpstan cache) for Implement and Verify; one folder per stage, outside the ticket folder |
| `…/<TICKET>/diff.patch` | `review.py` | The diff that was reviewed |
| `…/<TICKET>/feedback.md` | **you** (optional) | Feedback read by Retro |
| `<worktree-base>/<TICKET>/` (default `/srv/claude-workflow/worktrees`) | `base.py` / `git_host.py` | The git worktree with the code changes |
