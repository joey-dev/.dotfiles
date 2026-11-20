---
name: plan
description: Stage 4 — Implementation plan and adversarial self-review into 04-plan.md.
---

# Plan Stage

1. Read `01-ticket.md`, `02-findings.md`, and `03-qa.md`. Where `03-qa.md` says something changed from the ticket, `03-qa.md` wins.
2. Write `04-plan.md`. Start it with:
   - **Size**: one line, in plain words: a small change, or a project. If it is really several independent pieces, say so and propose an order.
   - **Approaches**: two or three real ways to build it, each grounded in what the code already does, with what it trades off. Drop any that work against the *why* in `03-qa.md`. Say which one you picked and why. When there is only one sensible way, say so and why the others don't fit.
3. Then write concrete steps, exact file paths, edge-case handling, and a test plan.
4. Mark every decision that `03-qa.md` did not make as *planner's call: <reason>*, so the user can spot and check it. Decisions in `03-qa.md` (from the user or marked *Claude's call*) are settled; don't reopen them.
5. If you hit a genuine unknown that was not answered in `03-qa.md`, write `blocked-questions.md` and stop instead of guessing. This includes:
   - a choice between approaches that would give the **user** a different result (behavior, screens, data), and `03-qa.md` doesn't say which they want. A choice that only changes the code's internals is your call.
   - work that turns out **much bigger** than `03-qa.md` assumed.
6. Also write `tests.txt`: one line per test to run. List every test you plan to create or edit. Each line is `<command-name> [parameter=value ...]`, using only the commands from the list in the prompt, e.g. `phpunit filter=InvoiceTest`. Values cannot contain spaces, and only parameters marked "settable in tests.txt" can be set. `host` and `container` commands run only in Verify. `#` comments and blank lines are allowed.
7. Never write or run a DB migration. For schema changes only edit or add table files in `legacy/app/atlas-migrations/customer/schema/tables`, and note in the plan that the human runs the migration.

## When acting as the plan reviewer

1. Start `04-plan-review.md` with `APPROVED` or `CHANGES_REQUESTED`.
2. **Builder check.** Read the plan as the implementer would, who can't ask anyone. List what you would still need to know, and sort each point:
   - **answered already** in `01-ticket.md`, `02-findings.md`, `03-qa.md` or the code: request that the plan says it;
   - **minor**: a sensible implementer could settle it without changing what gets built: request that the plan settles it as a *planner's call*;
   - **only the user can answer**, and the answer changes what gets built: write it to `blocked-questions.md` and stop.

   On the **last** review pass (the prompt says `pass N/N`), minor points alone are not a reason for `CHANGES_REQUESTED`: approve, and note them in the review. The implementer settles them as *implementer's call*. Running out of passes fails the whole stage.
3. Check that the plan follows `03-qa.md`, including its "Changed from the ticket" section.
4. Check that `tests.txt` lists every test the plan creates or edits.
