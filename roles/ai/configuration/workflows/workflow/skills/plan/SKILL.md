---
name: plan
description: Stage 4 — Implementation plan and adversarial self-review into 04-plan.md.
---

# Plan Stage

1. Read `01-ticket.md`, `02-findings.md`, and `03-qa.md`.
2. Write `04-plan.md` with concrete steps, exact file paths, edge-case handling, and a test plan.
3. If you hit a genuine unknown that was not answered in `03-qa.md`, write `blocked-questions.md` and stop instead of guessing.
4. When acting as the plan reviewer, start `04-plan-review.md` with `APPROVED` or `CHANGES_REQUESTED`.
5. Also write `tests.txt`: one line per test to run. List every test you plan to create or edit. Use `flake: <shell command>` (runs in the sandbox) or `docker: <test_runner.sh arguments>` (first argument: `unit`, `integration`, `api`, `mobile-api`, `acceptance` or `codecept-build`; runs only in Verify). `#` comments and blank lines are allowed.
6. Never write or run a DB migration. For schema changes only edit or add table files in `legacy/app/atlas-migrations/customer/schema/tables`, and note in the plan that the human runs the migration.
7. When acting as the plan reviewer, also check that `tests.txt` lists every test the plan creates or edits.
