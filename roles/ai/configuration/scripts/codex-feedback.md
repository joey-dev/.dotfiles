# Feedback on plan.md

The proposed workflow makes sense. Keep shell for launching sandboxes and use
a small local Python controller to manage the workflow. A workflow engine is
not needed yet.

## Responsibilities

| Part | Responsibility |
| --- | --- |
| Local controller | Retrieve Jira tickets, manage steps, request approval, resume, and record logs |
| Sandbox launcher | Apply mounts and network policy for the selected step |
| Skills | Guide Claude through brainstorming, planning, execution, and review |
| Saved artifacts | Preserve ticket snapshots, plans, implementation notes, and review findings |

The controller decides when a stage can advance. Skills guide the work within
that stage. A successful Claude exit alone does not establish approval or a
successful review.

## Decisions to resolve

1. **Persist structured workflow state.** A step name in `currentStep.md` cannot
   distinguish work that has not started, failed halfway, or finished and awaits
   approval. Store the step, status, attempt, and approval in structured state.
   Markdown can remain the readable view. Save updates atomically and prevent
   two commands from operating on the same ticket simultaneously.

2. **Tie approvals and reviews to specific artifacts.** Changes to an approved
   plan invalidate its approval. Record which commit and uncommitted changes a
   review examined. Preserve earlier attempts and findings rather than
   overwriting them.

3. **Separate provider access from command network access.** Completely disabling
   networking also disconnects Claude from its provider during execution and
   review. Consider a restricted proxy or separate network boundaries. The
   current launcher shares the host network. Bubblewrap requires explicit
   network isolation. References: [Claude network configuration](https://code.claude.com/docs/en/network-config)
   and [Bubblewrap namespace options](https://github.com/containers/bubblewrap/blob/main/bwrap.xml).

4. **Define the host commit contract.** Making a helper script read-only protects
   its contents, but does not by itself prevent pushing or make host execution
   safe. The host should perform a fixed operation against a known repository,
   without executing arbitrary commands supplied by the sandbox. Account for
   repository hooks when deciding how commits run. The known Git worktree
   metadata visibility issue still needs a design decision.

5. **Prepare dependencies before offline execution.** Make Nix packages, project
   dependencies, and test services available before execution starts. Missing
   dependencies should produce an explicit blocked result and preparation step.

6. **Use one canonical location for each artifact.** Separate document directories
   and per-stage read-only mounts fit the workflow. Setup currently creates
   `docs` and `info` inside the sandbox, while the mounts use the separate
   `.agents/docs` tree. Resolve that duplication.

## Implementation direction

Keep the existing shell launcher as a foundation. Bash can implement the full
flow, but approvals, retries, review loops, and recovery after interruption make
it harder to follow and test.

Start with a local controller for the interactive workflow. Reconsider a
workflow engine if the system needs multiple machines, queued unattended jobs,
or shared operation by several people.

This feedback is a proposal for later discussion, not an approved implementation
plan.
