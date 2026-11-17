# Claude workflow requirements

This inventory covers the workflow under `roles/ai`. It draws on the stage skills, runtime prompts, configuration, tests, and Home Manager wiring. The [issues report](WORKFLOW-ISSUES.md) records where the implementation falls short or the expected behavior needs a decision.

## Entry point and configuration

- Enable the role with `roles.ai.enable`. Home Manager packages the Python 3.12+ CLI, installs the default configuration and skills, and supplies the launcher's runtime tools. The Python entry point is `claude_workflow.cli:main`. [Role](../../ai.nix) · [Package](workflow/pyproject.toml)
- Accept a Jira ticket ID, optional `--config`, optional `--from-stage`, and `--auto`. Run Intake → Explore → Q&A → Plan → Implement → Verify → Review → Retro. Without an explicit start stage, resume the current stage or run the first incomplete stage. A completed ticket exits successfully. [CLI](workflow/claude_workflow/cli.py) · [State](workflow/claude_workflow/state.py)
- By default, offer continue, retry, or abort after each successful stage. `--auto` skips those gates. Q&A, escalation Q&A, and Retro remain interactive. Stage failure, abort, or exhausted escalations stop the run with a nonzero result. [Pipeline](workflow/claude_workflow/pipeline.py)
- Load explicit JSON configuration, then the XDG config location when no explicit path is given, then built-in defaults when no file is found. Support repository, state, worktree, KB, skills and optional Nix flake paths, verification commands, retry limits, and per-stage model, thinking, repository access, networking, MCP configuration and tools. Defaults are the current repository, ticket state under `~/.local/state/claude-workflow` in the shipped JSON, worktrees beneath that directory, KB at `~/notes/work-kb`, two plan review passes and three escalations per stage. Verification commands and flake are optional. [Loader](workflow/claude_workflow/config.py) · [Shipped settings](config.json)

## Stage inputs and outputs

| Stage | Requirements and artifacts |
| --- | --- |
| Intake | Use Atlassian MCP to fetch the ticket, summary, description, comments, and linked issues. Write `01-ticket.md` with summary and issue type, acceptance criteria, comments and decisions, dependencies, and initial ambiguities. [Skill](workflow/skills/intake/SKILL.md) · [Runner](workflow/claude_workflow/stages/intake.py) |
| Explore | Read the ticket, repository and relevant read-only KB notes. Identify modules, entry points, tests, reusable patterns, legacy quirks and risks. Write those findings and open questions to `02-findings.md`. [Skill](workflow/skills/explore/SKILL.md) |
| Q&A | Read the ticket and findings. Ask a concise numbered batch grouped by behavior, edge cases, compatibility, and testing. Save questions and answers incrementally in `03-qa.md` and support interrupted-session resume. [Skill](workflow/skills/qa/SKILL.md) · [Runner](workflow/claude_workflow/stages/qa.py) |
| Plan | Use the ticket, findings and Q&A to write `04-plan.md` with concrete steps, exact paths, edge cases and a test plan. Run capped adversarial review passes. Start `04-plan-review.md` with `APPROVED` or `CHANGES_REQUESTED` and revise in response to concrete feedback. [Skill](workflow/skills/plan/SKILL.md) · [Runner](workflow/claude_workflow/stages/plan.py) |
| Implement | Apply the plan in the isolated writable ticket worktree, reuse repository patterns and helpers, and keep functions small, typed and tested. Write `05-implement.md`. The host prepares or reuses the ticket branch and worktree, records the base commit, and commits dirty changes after a successful stage. [Skill](workflow/skills/implement/SKILL.md) · [Runner](workflow/claude_workflow/stages/implement.py) |
| Verify | Run each configured command in the worktree and record its result, exit status on failure, and output in `06-verify.md`. Use the configured Nix development environment when available. Fail the stage if any check fails and record an explicit skip when the command list is empty. [Runner](workflow/claude_workflow/stages/verify.py) |
| Review | Capture `diff.patch` relative to the recorded base, including untracked changes. Independently review correctness and conventions against ticket and plan context. Look for edge cases, regressions, missing tests, readability and maintainability problems. Cite paths and lines, skip trivial style comments, and combine both lens reports into `07-review.md`. [Skill](workflow/skills/review/SKILL.md) · [Runner](workflow/claude_workflow/stages/review.py) |
| Retro | Interactively summarize verification and review, record human feedback and legacy surprises, and propose concrete minimal KB or skill diffs in `08-retro.md`. KB edits require explicit approval. Support interrupted-session resume. [Skill](workflow/skills/retro/SKILL.md) · [Runner](workflow/claude_workflow/stages/retro.py) |

## State, escalation and isolation

- Persist ticket ID, current and completed stages, interactive session IDs, branch, worktree, base commit and escalation counts in per-ticket `state.json`. Save the stage before execution and completion afterward. Replace the checkpoint atomically. [State](workflow/claude_workflow/state.py) · [Pipeline](workflow/claude_workflow/pipeline.py)
- On a genuine Plan or Implement unknown, write `blocked-questions.md` and stop. Notify the user when possible, run interactive Q&A, append answers to `03-qa.md`, clear the blocker and retry within the configured cap. Keep artifacts concise and factual, citing paths, symbols and observed output. [Shared skill](workflow/skills/shared/SKILL.md) · [Pipeline](workflow/claude_workflow/pipeline.py)
- Keep branch, diff and commit operations on the host. Workflow agents must avoid Git commands, and the host helpers have local-only responsibilities. [Shared skill](workflow/skills/shared/SKILL.md) · [Host helpers](workflow/claude_workflow/git_host.py)
- Run Claude through Bubblewrap with a per-ticket home, writable notes, the shared and current stage skills, and read-only KB, flake and MCP mounts when supplied. Mount eligible repository directories in the configured mode and mask their root `.git`. Carry Claude authentication and settings into the isolated environment. [Sandbox](workflow/claude_workflow/sandbox.py)
- For stages with restricted networking, isolate the network namespace and allow API access through the CONNECT proxy to `api.anthropic.com:443` by default. The proxy accepts only CONNECT to its configured host and port. [Runner](workflow/claude_workflow/claude_runner.py) · [Proxy](workflow/claude_workflow/net_proxy.py)

## Shipped stage defaults

`Read/Write` below lists Claude tools. The repository column describes the configured mount mode. [Defaults](config.json)

| Stage | Model / thinking | Repository | Network | Tools |
| --- | --- | --- | --- | --- |
| Intake | Sonnet / medium | None | Allowed | Read, Write, Atlassian MCP |
| Explore | Opus / high | Read-only | Allowed | Read, Glob, Grep, Write, WebFetch |
| Q&A | Sonnet / medium | Read-only | Restricted | Read, Glob, Grep, Write |
| Plan | Opus / high | Read-only | Allowed | Read, Glob, Grep, Write, WebFetch |
| Implement | Sonnet / high | Read/write | Restricted | Read, Edit, Write, Glob, Grep, Bash |
| Verify | Sonnet / low | Read/write | Restricted | Empty config, host command execution in current code |
| Review | Opus / high | Read-only | Restricted | Read, Glob, Grep, Write |
| Retro | Sonnet / medium | Read-only setting, no repository supplied | Restricted | Read, Write |
