# Critical Review of Ideas & Architecture Approaches

> Companion to [00-jira-workflow.md](./00-jira-workflow.md).

---

## Critical Review of Proposed Ideas

### Keep & Prioritize (High Value)

- **Stage-isolated skills:** Bind-mounting only the active stage's skills into `bwrap` prevents prompt bloat and keeps planning rules out of the coder's context.
- **Read-only Personal Knowledge Base (KB):** Huge token saver on a 12-year-old 200k+ LOC mono-repo. Keep it **curated and human-approved** (a post-run agent proposes KB updates; you approve the diff) so stale notes don't poison future runs.
- **Adversarial read-only code review:** Framing the reviewer as reviewing *someone else's* PR in a read-only repo reduces rubber-stamping.
- **Single-step retry with modified skills:** Saving each stage's inputs/outputs in a ticket run directory makes re-running one stage trivial.
- **Human feedback -> retrospective agent:** Recording why you disliked a diff and running a retro step after acceptance is the fastest way to harden skills.

### Simplify or Adjust (Watch Out For)

- **Multi-model subagent reviews + combiner + validator:**
  - *Risk:* 5–7x token cost and latency; weaker models produce noisy false positives on legacy code.
  - *Better v1:* Run **2 focused review passes** (e.g., **Correctness/Edge Cases** and **Repo Conventions/Legacy Pitfalls**) on strong models, then fix. Add multi-model voting later only if bugs slip through.
- **Unbounded plan-review loops:**
  - *Risk:* Loops without a cap turn into bike-shedding and scope creep.
  - *Better v1:* **Cap at 1–2 passes** with a strict rubric (missing edge cases, wrong paths, contradictions only).
- **Host-side git proxy inside `bwrap`:**
  - *Risk:* In a `git worktree`, `.git` is a pointer file to the main repo; building a host RPC proxy for `git add/commit` adds complexity you may not need.
  - *Better v1:* Hide `.git` inside `bwrap` and let the **host orchestrator script** run `git status`/`git diff`/`git add`/`git commit` between stages (and optionally expose a read-only `git diff` snapshot file if the reviewer needs it).

---

## Architecture Approaches

| Approach | How it works | Pros | Trade-offs |
|---|---|---|---|
| **A. Bash + `bwrap` + Stage Files (Recommended)** | `claude-workflow.sh` calls small stage scripts (`01-intake.sh`, etc.), passing `.md`/`.json` artifacts in a ticket state dir. | Zero new deps, super easy to inspect/re-run 1 stage while tuning skills, matches `claude-workflow.sh`. | Complex parallel queues or retry loops get verbose in Bash later. |
| **B. Python + `bwrap` + Stage Files** | Same `bwrap` + `claude` CLI + stage files, orchestrated by Python. | Clean state machine, JSON handling, parallel worker pool, and Docker lockfile queue. | Slightly more upfront boilerplate than Bash. |
| **C. Claude Agent SDK / `stream-json`** | Programmatic SDK loop instead of CLI stages + files. | Tight control over tool calls in code. | Harder to drop into interactive Q&A or manually inspect/edit stage files while tuning skills. |
