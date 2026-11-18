# Claude workflow guide

## Quick overview

`claude-workflow` takes a **Jira ticket** through research, clarification, planning, implementation, verification, and review. It makes code changes in a **separate ticket worktree** and commits locally after the final human check. Publishing the branch or opening a merge request is a separate manual action.

1. Enable `roles.ai.enable` in Home Manager. Make sure Claude Code is authenticated, configure the **Atlassian MCP** connection, and set the repository's **`verify_commands`**.
2. From the repository root, run `claude-workflow PROJ-123`.
3. Read the stage output at each gate. Enter **c** to continue, **r** to retry, or **a** to stop. Answer Claude's questions during **Q&A** and inspect the proposed changes during **Retro**.
4. If interrupted, run the same command again. The workflow resumes the current stage or returns to its pending approval.

```sh
claude-workflow PROJ-123
claude-workflow PROJ-123 --only-stage explore
claude-workflow PROJ-123 --from-stage implement
```

The second command reruns **Explore** and stops after that stage's approval. The third restarts at **Implement** and continues through the remaining stages. Both require earlier stages to be completed and invalidate downstream completion so changed inputs get picked up on the next run.

## Setup on NixOS

Home Manager installs the CLI and supplies the default configuration at `${XDG_CONFIG_HOME:-~/.config}/claude-workflow/config.json`. Use `--config /path/to/config.json` for repository-specific settings. Launch from the repository root unless you set `repo_path` explicitly. The [Home Manager role](../../ai.nix) and [shipped configuration](config.json) show the defaults.

- **Jira access.** Configure a Claude user-level MCP server named `atlassian`, or set `stages.intake.mcp_config` to the MCP JSON for that stage. The server must expose the Atlassian tools allowed by Intake. Keep credentials in your Claude and MCP setup.
- **Verification.** Set `verify_commands` to the project's linters and unit tests. The shipped list is empty, and Verify stops until commands are supplied. Commands run from the ticket worktree and should leave its diff unchanged.
- **Project tools.** Set `flake_path` if Implement and Verify need a shared Nix development shell. The flake is optional and applies only to those stages. The Verify sandbox defaults to restricted networking, so prepare required dependencies in advance.
- **Knowledge base.** Set `kb_path` to the personal KB directory, or keep the default `~/notes/work-kb`. Applicable stages can read notes when the directory exists.
- **Skill tuning.** Set `skills_base` to your editable copy of the workflow skills if you want to experiment. Preserve the `shared/SKILL.md` and `<stage>/SKILL.md` directory layout.

## What each stage does

| Stage | What happens | Where to look |
| --- | --- | --- |
| **1. Intake** | Fetches the Jira ticket, acceptance criteria, comments, and linked issues. | `01-ticket.md` |
| **2. Explore** | Reads the repository and relevant KB notes. Records entry points, reusable patterns, tests, legacy behavior, and open questions. | `02-findings.md` |
| **3. Q&A** | Asks a batch of clarifying questions and saves answers incrementally. | `03-qa.md` |
| **4. Plan** | Drafts steps and a test plan. An adversarial reviewer can request revisions. The default cap is two review passes, and an approved plan is required to proceed. | `04-plan.md`, `04-plan-review.md` |
| **5. Implement** | Creates or reuses the ticket worktree and applies the plan. Reads Q&A, including escalation answers, and addresses applicable findings from any previous code review. | Ticket worktree, `05-implement.md` |
| **6. Verify** | Runs the configured checks inside Bubblewrap. Records results and fingerprints the diff after confirming the checks left it unchanged. | `06-verify.md` |
| **7. Review** | Checks that the diff still matches verification. Runs independent correctness and conventions reviews. Both must approve. | `diff.patch`, `07-review.md`, and one file per reviewer |
| **8. Retro** | Shows the worktree and diff locations. Discusses the changes and human feedback, and proposes skill or KB updates. Final approval triggers the local commit when there are changes to commit. | `feedback.md` if supplied, `08-retro.md` |

## Where state and changes live

Ticket artifacts and the checkpoint live under `${XDG_STATE_HOME:-~/.local/state}/claude-workflow/<TICKET>/` by default. Worktrees go under the sibling `worktrees/<TICKET>/` directory within the workflow state root. The workflow uses the lowercase ticket key for the branch name and records the starting commit so Verify and Review can compare against the same base.

The checkpoint tracks the current stage, completed stages, pending approval, interactive session IDs, and worktree details. A per-ticket lock prevents two processes from updating the same ticket at once. Keep the state directory if you want to resume a run or reuse its artifacts.

## Retry, resume, and review feedback

- **Resume.** Run `claude-workflow <TICKET>` with the same configuration and omit explicit stage selection. A completed stage awaiting approval returns to its gate. Interrupted Q&A or Retro can resume its Claude session.
- **Retry at a gate.** Enter **r** to rerun that stage. Existing worktree edits are kept, so review them if retrying Implement.
- **Run one stage.** Use `--only-stage <name>` to tune a skill or inspect an intermediate output. This executes the stage normally, including any side effects, and stops after approval. Running `--only-stage retro` still finalizes the branch.
- **Restart and continue.** Use `--from-stage <name>` when downstream work should be redone. After a rejected code review, use `--from-stage implement` to apply feedback, run checks again, and request a fresh review.
- **Answer a blocker.** If Plan or Implement writes `blocked-questions.md`, the workflow opens a short interactive Q&A. It keeps the blocker until answers are appended to `03-qa.md`, then retries the blocked stage within the configured cap.
- **Run with fewer prompts.** Use `--auto` to skip approval prompts. Q&A, blocker clarification, and Retro remain interactive.

## What the sandbox does

Bubblewrap gives each Claude stage the repository access it needs. Intake runs without the repository, Explore and Plan read it, and Implement can write to the ticket worktree. Code reviewers get a read-only worktree. Retro uses saved artifacts and the KB. The sandbox masks repository metadata at the mounted repository root and mounts the selected workflow skills and any KB read-only.

Stages with restricted networking use an allowlisted proxy for the Anthropic API when running Claude. Verify runs the configured commands directly in Bubblewrap with a scratch area and, by default, no network. The host handles worktree creation, diff capture, and the final local commit.

At final approval, the host compares the current diff against the verified one, even when the worktree is clean. If it creates a commit, it checks that the resulting diff still matches and that the worktree is clean. If either check fails, inspect the worktree and restart from Verify.

See the [requirements inventory](WORKFLOW-REQUIREMENTS.md) for full configuration defaults and the [issues report](WORKFLOW-ISSUES.md) for the original audit.
