---
name: implement
description: Stage 5 — Implement 04-plan.md inside the isolated worktree.
---

# Implement Stage

1. Follow `04-plan.md` step-by-step inside the worktree.
2. Reuse existing repo helpers and patterns; keep functions small, typed, and well-tested.
3. If you hit a genuine unknown or contradiction in the codebase, write `blocked-questions.md` and stop instead of guessing. The same when the change turns out **much bigger** than the plan (many more files, or a different approach): stop and ask, instead of quietly growing the scope.
4. Write a concise summary of changes to `05-implement.md`. List every place where you deviated from the plan or made a decision it didn't make, each as *implementer's call: <reason>*. Do not run `git` commands.
5. Run the `tests.txt` lines whose command runs in the `sandbox`, using the "Run it yourself" line from the command list in the prompt (with your own values). Lines are `<command-name> [parameter=value ...]`. `host` and `container` commands run only in Verify. If you add or rename a test, update `tests.txt`.
6. Never write or run a DB migration. For schema changes only edit or add table files in `legacy/app/atlas-migrations/customer/schema/tables`, and say in `05-implement.md` that the human runs the migration.
