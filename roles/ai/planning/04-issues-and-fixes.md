# Issues Found & Fixes Review

This document tracks every issue discovered during NixOS packaging, sandbox verification, and comparison with the legacy [claude-workflow.sh](../configuration/scripts/claude-workflow.sh) script.

---

## Part 1: Issues Already Fixed

### 1. `makeWrapperArgs` Quoting Failure in `ai.nix`
- **What is the issue?**
  `buildPythonApplication` failed in `fixupPhase` with:
  `makeWrapper doesn't understand the arg --prefix PATH : /nix/store/...`
- **Why is it an issue?**
  `wrapPythonPrograms` passes each element of `makeWrapperArgs` as a single quoted argument to `wrapProgram`, so `"--prefix PATH : ..."` was treated as one unknown flag instead of 4 separate tokens.
- **Options to fix/change:**
  1. Split `makeWrapperArgs` into separate list elements (`"--prefix"`, `"PATH"`, `":"`, `"..."`).
  2. Remove `makeWrapperArgs` and call `wrapProgram` directly in `postFixup`.
- **How we fixed it:**
  Replaced `makeWrapperArgs` with `postFixup` calling `wrapProgram $out/bin/claude-workflow` directly in [ai.nix](../ai.nix#L39-L43).

### 2. `PlanStage` Test Executed Real `bwrap` in Nix Build Sandbox
- **What is the issue?**
  `test_plan_stage_caps_review_loop_at_max_plan_reviews` failed with `FileNotFoundError: 'bwrap'` during `pytestCheckPhase`.
- **Why is it an issue?**
  `PlanStage` calls `run_headless_with_escalation()` in `stages/base.py`, which imported `run_claude_headless` directly. Monkeypatching only `plan_mod.run_claude_headless` left `base_mod.run_claude_headless` unpatched.
- **Options to fix/change:**
  1. Monkeypatch both `base_mod.run_claude_headless` and `plan_mod.run_claude_headless` in the test.
  2. Pass `run_claude_headless` as an injectable dependency to `run_headless_with_escalation()`.
- **How we fixed it:**
  Monkeypatched `base_mod.run_claude_headless` alongside `plan_mod.run_claude_headless` in [test_pipeline.py](../configuration/workflows/workflow/tests/test_pipeline.py#L168-L169).

### 3. Missing `--unshare-pid` in `bwrap` Sandbox
- **What is the issue?**
  `build_bwrap_command()` mounted `--proc /proc` without `--unshare-pid`.
- **Why is it an issue?**
  Without `--unshare-pid`, the sandbox shares the host PID namespace, allowing sandboxed processes to see and potentially signal other host processes running under the same UID.
- **Options to fix/change:**
  1. Add `--unshare-pid` to `build_bwrap_command()`.
- **How we fixed it:**
  Added `--unshare-pid` in [sandbox.py](../configuration/workflows/workflow/claude_workflow/sandbox.py#L71).

### 4. `--unshare-net` Blocked `claude` From Reaching Anthropic API
- **What is the issue?**
  Stages with `allow_network: false` (`qa`, `implement`, `review`, `retro`) passed `--unshare-net` to `bwrap`, cutting off all network access including `api.anthropic.com`.
- **Why is it an issue?**
  `claude` is a cloud API client; with `--unshare-net` alone, every offline stage fails immediately with a connection error.
- **Options to fix/change:**
  1. **Practical:** Drop `--unshare-net` and rely on Claude tool rules (`--disallowedTools` / `settings.json`). Weak against unattended `Bash` commands (`python`, `nc`, `/dev/tcp`).
  2. **Strict:** Keep `--unshare-net` and run a host-side HTTP `CONNECT` allowlist proxy over a Unix socket bridged into the sandbox via `socat`.
- **How we fixed it:**
  Implemented the **Strict** option: [net_proxy.py](../configuration/workflows/workflow/claude_workflow/net_proxy.py) (`ConnectAllowlistProxy` allowing only `api.anthropic.com:443`), `socat` bridge in [sandbox.py](../configuration/workflows/workflow/claude_workflow/sandbox.py#L22-L31), automatic proxy lifecycle in [claude_runner.py](../configuration/workflows/workflow/claude_workflow/claude_runner.py#L31-L85), and `pkgs.socat` in [ai.nix](../ai.nix#L41).

### 5. Missing Claude Auth & Session Files (`~/.claude`, `~/.claude.json`)
- **What is the issue?**
  `sandbox.py` did not mount `~/.claude` or `~/.claude.json` into `bwrap`.
- **Why is it an issue?**
  `claude` could not read `.credentials.json` or session files, forcing login on every step (or failing headless runs) and breaking `--resume` in Stage 3 (`qa`) and Stage 8 (`retro`).
- **Options to fix/change:**
  1. Bind-mount host `~/.claude` and `~/.claude.json` directly into `bwrap` (relying on `settings.json` deny rules to block Claude's `Read` tool from `.credentials.json`).
  2. Create an isolated per-sandbox `$HOME` and copy only `.credentials.json` (`0600`), as `claude-workflow.sh` does (see Issue #11 below).
- **How we fixed it:**
  Implemented Option 1 (`_append_claude_auth_mounts`) in [sandbox.py](../configuration/workflows/workflow/claude_workflow/sandbox.py#L51-L62). (See Issue #11 for tightening this further.)

### 6. `mcp_config` Not Mounted & `SKILL.md` Not Referenced in Prompts
- **What is the issue?**
  `--mcp-config <path>` was passed to `claude` without mounting `<path>` into `bwrap`, and stage skills were mounted at their host path without telling `claude` to read them.
- **Why is it an issue?**
  `claude` cannot access unmounted `mcp_config` files inside `bwrap`, and only auto-discovers skills under `~/.claude/skills` or `.claude/skills`.
- **Options to fix/change:**
  1. `--ro-bind` `mcp_config` in `sandbox.py` and prepend explicit `SKILL.md` paths to stage prompts.
  2. Mount stage skills directly to `$HOME/.claude/skills/` inside an isolated sandbox `$HOME`.
- **How we fixed it:**
  Implemented Option 1 in [sandbox.py](../configuration/workflows/workflow/claude_workflow/sandbox.py#L102-L104) and `skill_prompt_prefix()` in [base.py](../configuration/workflows/workflow/claude_workflow/stages/base.py#L80-L89).

---

## Part 2: Additional Issues Fixed (from `claude-workflow.sh` & Review)

### 7. Missing `--add-dir` & Scattered Host-Path Binds Instead of Clean Sandbox `$HOME`
- **What is the issue?**
  `sandbox.py` binds `repo_dir`, `state_dir`, `kb_dir`, and `skills_dirs` at their raw host paths, and `claude_runner.py` never passes `--add-dir` to `claude`.
- **Why is it an issue?**
  Claude Code restricts file tools (`Read`/`Edit`/`Write`/`Glob`) to the `--chdir` directory unless extra directories are explicitly granted with `--add-dir`. When `workdir` is `repo_dir`, Claude may get blocked or prompt for permission when reading/writing `state_dir` (`01-ticket.md`, `02-findings.md`, etc.), `kb_dir`, or `skills_dirs`. Additionally, scattered host paths expose host directory structure unnecessarily compared to `claude-workflow.sh`'s clean `$HOME` layout (`$HOME/notes`, `$HOME/<repo>`, `$HOME/flake`, `$HOME/.claude/skills`).
- **Options to fix/change:**
  1. Keep host paths and pass `--add-dir` for `state_dir`, `kb_dir`, `skills_dirs`, and `flake_dir` in `claude_runner.py`.
  2. Adopt `claude-workflow.sh`'s sandbox `$HOME` layout (`--tmpfs /home`, bind a dedicated sandbox home to `$HOME`, `state_dir` → `$HOME/notes`, `repo` → `$HOME/<repo>`, `flake` → `$HOME/flake`, `skills` → `$HOME/.claude/skills`) **and** pass `--add-dir` for each.
- **How we fixed it (Option 2):**
  Updated [sandbox.py](../configuration/workflows/workflow/claude_workflow/sandbox.py#L64-L108) (`sandbox_paths()` + `build_bwrap_command()`), [claude_runner.py](../configuration/workflows/workflow/claude_workflow/claude_runner.py#L29-L41) (`--add-dir`), and all stage modules to use `$HOME`-relative sandbox paths (`$HOME/notes`, `$HOME/<repo>`, `$HOME/kb`, `$HOME/flake`, `$HOME/.claude/skills`).

### 8. Missing `--permission-mode bypassPermissions` for Unattended Runs
- **What is the issue?**
  `claude_runner.py` does not pass `--permission-mode bypassPermissions` (unlike `claude-workflow.sh` line 145).
- **Why is it an issue?**
  To let Claude run autonomously without interrupting for tool approval prompts, Claude Code needs `--permission-mode bypassPermissions` (while `bwrap`, `--unshare-net` + `ConnectAllowlistProxy`, and `.git` masking enforce the real security boundary).
- **Options to fix/change:**
  1. Pass `--permission-mode bypassPermissions` in `_common_claude_flags()` for all sandboxed stages.
  2. Make `permission_mode` configurable in `StageConfig` (defaulting to `"bypassPermissions"`).
- **How we fixed it (Option 1):**
  Added `--permission-mode bypassPermissions` to `_common_claude_flags()` in [claude_runner.py](../configuration/workflows/workflow/claude_workflow/claude_runner.py#L31-L36).

### 9. Missing `nix develop <flake>` & Dotfiles Template Flake Support
- **What is the issue?**
  The project's `flake.nix` is not in the mono-repo—it lives in the dotfiles templates directory (`~/.agents/shared/flakes/latest` in `claude-workflow.sh`). `claude-workflow` currently neither mounts the flake directory nor runs `nix develop <flake> --command ...`.
- **Why is it an issue?**
  Without entering the template flake's devShell, Stage 5 (`implement`) and Stage 6 (`verify`) will lack the project's compilers, linters, and test runners in `PATH`.
- **Options to fix/change:**
  1. Add `flake_path: Path | None` to `WorkflowConfig` (and `config.json`), `--ro-bind` it into the sandbox (`$HOME/flake`) + `--add-dir`, and wrap `bwrap` (and `verify_commands`) with `nix develop <flake_path> --command ...` when set.
  2. Rely on manual `nix develop ... -c` inside `verify_commands` (leaves Stage 5 `implement` without devShell tools).
- **How we fixed it (Option 1):**
  Added `flake_path: Path | None` to [config.py](../configuration/workflows/workflow/claude_workflow/config.py#L67) and [config.json](../configuration/workflows/config.json#L6), mounted it RO at `$HOME/flake` + `--add-dir`, and wrapped `bwrap` in [claude_runner.py](../configuration/workflows/workflow/claude_workflow/claude_runner.py#L51-L54) and `verify_commands` in [verify.py](../configuration/workflows/workflow/claude_workflow/stages/verify.py#L30-L37) with `nix develop <flake_path> --command ...`.

### 10. Broad `/etc` Bind & Missing NixOS Profile Paths
- **What is the issue?**
  `sandbox.py` binds all of `/etc` (`--ro-bind /etc /etc`) and does not mount `/etc/profiles`, `/etc/static`, or `~/.nix-profile` (which `claude-workflow.sh` lines 155–167 explicitly handle).
- **Why is it an issue?**
  Mounting all of `/etc` exposes unrelated host config, while omitting `/etc/profiles`, `/etc/static`, and `~/.nix-profile` can break NixOS tools/binaries referenced via profile symlinks.
- **Options to fix/change:**
  1. Replace `--ro-bind /etc /etc` with minimal binds (`/etc/ssl`, `/etc/resolv.conf`, `/etc/hosts`, `/etc/profiles`, `/etc/static`) plus resolved `readlink -f ~/.nix-profile` (matching `claude-workflow.sh`).
  2. Keep `/etc` RO and only add `/etc/profiles`, `/etc/static`, and `~/.nix-profile`.
- **How we fixed it (Option 1):**
  Updated `_SYSTEM_RO_PATHS` and `build_bwrap_command()` in [sandbox.py](../configuration/workflows/workflow/claude_workflow/sandbox.py#L14-L26) to mount `/etc/profiles`, `/etc/static`, `/etc/resolv.conf`, `/etc/ssl`, `/etc/hosts`, and resolved `~/.nix-profile` instead of all of `/etc`.

### 11. Host `~/.claude` RW Bind vs Isolated Sandbox `$HOME` + Copied Credentials
- **What is the issue?**
  `sandbox.py` currently `--bind`s the real host `~/.claude` and `~/.claude.json` directly into `bwrap`.
- **Why is it an issue?**
  A RW bind on real `~/.claude` allows a sandboxed `claude` to modify host `settings.json`, hooks, or unrelated project state. `claude-workflow.sh` (lines 65–79, 111–120, 165–166) instead uses `--tmpfs /home`, binds a dedicated sandbox home to `$HOME`, and copies only `.credentials.json` (`chmod 600`, verifying it is not a symlink).
- **Options to fix/change:**
  1. Keep host `~/.claude` `--bind` (simpler, shares `--resume` and plugins automatically).
  2. Switch to per-ticket sandbox `$HOME` (`state_dir/home`) + copy `.credentials.json` (`0600`) + RO-bind `skills/` and `settings.json` into `$HOME/.claude/`.
- **How we fixed it (Option 2):**
  Added `prepare_sandbox_home()` in [sandbox.py](../configuration/workflows/workflow/claude_workflow/sandbox.py#L111-L135) to create an isolated per-ticket `state_dir/home`, copy only `.credentials.json` (`0600`, symlink-checked) and `.claude.json` (`0600`), and RO-bind host `~/.claude/settings.json`.

### 12. `review.py` Captures an Empty `diff.patch` After `implement.py` Commits
- **What is the issue?**
  `implement.py` calls `commit_stage()` on the host after Stage 5, and then `review.py` (Stage 7) calls `capture_diff(worktree)` which defaults to `git diff HEAD`.
- **Why is it an issue?**
  Once changes are committed on the ticket branch, `git diff HEAD` is empty, so `diff.patch` in Stage 7 will contain no changes to review.
- **Options to fix/change:**
  1. Record `base_commit` in `TicketState` when `ensure_worktree()` creates the branch, and pass `base_ref=state.base_commit` to `capture_diff()`.
  2. Diff against `origin/HEAD` or `merge-base HEAD main`.
- **How we fixed it:**
  Added `rev_parse_head()` in [git_host.py](../configuration/workflows/workflow/claude_workflow/git_host.py#L63-L65), `base_commit` in [state.py](../configuration/workflows/workflow/claude_workflow/state.py#L24), recorded `base_commit` in [implement.py](../configuration/workflows/workflow/claude_workflow/stages/implement.py#L24-L35), and passed `base_ref=ctx.state.base_commit or "HEAD"` to `capture_diff()` in [review.py](../configuration/workflows/workflow/claude_workflow/stages/review.py#L39-L42).
