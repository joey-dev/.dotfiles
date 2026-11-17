---
name: shared
description: Core rules shared across all claude-workflow pipeline stages.
---

# Shared Workflow Rules

- **Never guess on genuine unknowns.** In `plan` or `implement`, write `blocked-questions.md` in the ticket state directory and stop cleanly so the human can answer.
- **No git commands.** `.git` is hidden in the sandbox; the host orchestrator handles branches, diffs, and commits.
- **Keep artifacts concise and factual.** Cite exact file paths, symbol names, and observed outputs only.
