# Jira Ticket Workflow — Planning Notes

> Living document for designing a scripted, Claude-based workflow that turns Jira tickets into clean, working branches.

---

## Goal

Run a script with a **Jira ticket ID** as a parameter and end up with a **working, clean git branch** where the issue is fixed.

---

## Constraints & Context

- **AI tool:** Claude Code only (work policy).
- **Runtime OS:** **NixOS only** (the script runs on NixOS, so `bwrap`, `jq`, `git`, `notify-send`, etc. are available).
- **Codebase:** 200k+ LOC mono-repo, 12+ years old (contains legacy code).
- **Clarification needed:** Many Jira tickets lack full context, so the workflow **must ask clarifying questions** before implementing.
- **Rollout:**
  1. **First:** Run **step-by-step** to inspect results and tinker with skills/prompts.
  2. **Later:** Run **multiple tickets in parallel**.
- **Existing setup in `roles/ai/`:**
  - `configuration/claude/CLAUDE.md` — personal & formatting preferences.
  - `configuration/claude/settings.json` — `superpowers` plugin enabled, `notify-send` hooks on `Notification` and `Stop`, `git push`/`git commit` set to `ask`.
  - `configuration/scripts/claude-workflow.sh` — currently empty.

---

## Open Questions

*All core architecture questions resolved — see [02-design.md](./02-design.md) for the full design.*

---

## Decisions Made

1. **Custom skills over `superpowers`:** Build and fine-tune custom skills tailored to the mono-repo and workflow.
2. **Separate scriptable stages** (over one long interactive session):
   - Enables **least-privilege sandboxing** per stage (e.g. `bwrap` read-only repo during exploration/planning).
   - Keeps **context clean** in a 200k+ LOC repo by passing structured artifacts between stages instead of carrying 100k tokens of search history.
   - Makes **skill tuning** repeatable (re-run a single stage on saved artifacts).
   - Unlocks **parallel execution** later (prep stages run async, notify when human input is needed).
3. **Interactive Q&A stage with crash-safe persistence:**
   - Use an **interactive Claude Q&A stage** (so it can ask dynamic follow-ups).
   - Claude should **batch its questions up front** rather than drip-feeding them across stages.
   - **Persist answers incrementally** (write Q&A / decisions to disk as you go, plus support `--resume`) so progress isn't lost if the session dies halfway through.
4. **Jira integration via Atlassian MCP:**
   - Use the existing **Atlassian MCP** in the intake stage to fetch ticket details, comments, and linked issues.
   - Keeps Jira/network access isolated to the intake stage only.
5. **Two-tier verification (NixOS `flake.nix` vs. Docker Compose):**
   - **Linters & unit tests** can run directly on **NixOS via `flake.nix`** with no DB/containers -> safe to run **in parallel per worktree**.
   - **Integration & API tests** need the **Docker Compose stack** (MySQL, server, PHP, Vue, etc.), which has **port conflicts** and takes **10+ min** for the full suite -> cannot run concurrently across worktrees without port isolation (must be serialized/queued, targeted, or left to CI).
6. **Definition of "done" & safety boundaries:**
   - Functionally solves the ticket, reads like a good developer wrote it, and passes code review cleanly.
   - **Never push code** automatically.
   - **Approval gate between every step** initially (toggleable off later).
   - **Stage-isolated skills** (e.g., planning skills hidden from the coding agent).
   - **Read-only Personal Knowledge Base (KB)** outside the repo (repo map, code pointers, past Q&A/assumptions), updated via a separate step/agent.
   - **Retrospective / feedback loop** when human review rejects or changes code, to improve skills and the KB.
7. **Orchestrator: Approach B (Python + `bwrap` + Stage Files):**
   - Small, single-purpose Python modules with **strict type annotations** (checked with `pyright` / `mypy`), **dataclasses**, and **docstrings**.

---

## Risks / Things to Design Around

- **Handoff loss between stages:** Later stages only know what earlier stages write down -> requires clear, structured stage artifacts (`findings.md`, `questions.md`, `plan.md`).
- **Verification environment:** `bwrap` isolates files well, but PHP/Symfony + Vue tests/linters may need DB/Redis/Docker sockets or `vendor/`/`node_modules/` access.
- **Parallel worktree collisions:** Parallel tickets need `git worktree` isolation and care around shared state (test DBs, caches, ports).
