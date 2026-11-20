---
name: review
description: Stage 7 — Adversarial read-only code review of diff.patch, one lens per run.
---

# Code Review Stage

The prompt names **one lens** (correctness or conventions), the input files, and the report file to write. Review only through that lens; the other lens runs separately.

If the prompt starts with **"Validation pass"**, skip everything below and follow [Validation pass](#validation-pass) instead.

Treat the change as **someone else's merge request**. Your report goes back to Implement as a fix list, so every blocking finding costs a fix loop: only block on issues that are real and worth that cost.

## Inputs

- `diff.patch` — the change under review. Only lines added or changed in it are in scope.
- `01-ticket.md` — what the change should do (the author's intent).
- `03-qa.md` — the user's answers, including any escalation sections at the end. Where it disagrees with `01-ticket.md` (see its "Changed from the ticket" section), `03-qa.md` wins: a ticket requirement that `03-qa.md` changed or dropped is not missing.
- `04-plan.md` — how the author planned to do it.
- The repository (read-only) — read surrounding code to confirm a finding, not to hunt for problems outside the diff.
- `CLAUDE.md` / `AGENTS.md` files in the repo — a rule applies to a changed file only if the rule file sits in that file's directory or a parent directory.

## Lenses

- **Correctness:** logic bugs, unhandled edge cases, wrong error handling, regressions, and behavior that does not match `01-ticket.md` or `04-plan.md`.
- **Conventions:** departures from the patterns of surrounding code, duplicated logic where a repo helper already exists, misleading names, unnecessary complexity, and violations of a scoped `CLAUDE.md` rule.

## Process

1. Read the input files and summarize for yourself what the change is meant to do.
2. Go through `diff.patch` file by file and list candidate issues for your lens.
3. **Validate each candidate** before reporting it. Open the code and confirm it: the variable really is undefined, the branch really is reachable, the rule really applies to this path. Drop anything you cannot confirm.
4. Sort what remains into **blocking** and **non-blocking** (rules below).
5. Write the report.

## Blocking vs. non-blocking

**Blocking** (needs `CHANGES_REQUESTED`) — you are confident it is real and it is one of:

- Code that will not parse, compile, or load (syntax errors, type errors, missing imports, unresolved references).
- Logic that produces wrong results for realistic inputs, or a regression in existing behavior.
- A requirement from `01-ticket.md` (as changed by `03-qa.md`) that is missing or implemented incorrectly.
- A clear violation of a scoped `CLAUDE.md` rule; quote the rule.

**Non-blocking** — worth mentioning, but the change can proceed: naming, readability, minor duplication, small simplifications. Keep these few.

**Do not report:**

- Issues in code the diff did not touch (pre-existing issues).
- Code that looks wrong but is correct once you read the context.
- Nitpicks a senior engineer would not raise, or style a linter or formatter handles.
- Issues explicitly silenced in the code (e.g. a lint-ignore comment).
- Anything you are not sure is real. False positives waste a fix loop.

## Suggested tests (correctness lens only)

If you believe a test will fail, or a missing test would expose a bug:

1. Read `tests.txt` first. You only have the Write tool, so rewrite the file with **all existing lines unchanged** and your lines appended under a `# suggested by review` heading.
2. Use the line format `<command-name> [parameter=value ...]` with only the commands from the list in the prompt (e.g. `phpunit filter=InvoiceTest`). Values cannot contain spaces, and only parameters marked "settable in tests.txt" can be set.
3. Also report it as a blocking finding, so Implement knows why the test was added.

Changing `tests.txt` sends the ticket back to Implement. Do not edit it for any other reason, and never edit it in the conventions lens.

## Report format

Write the report to the file named in the prompt. The **first line** must be exactly `APPROVED` or `CHANGES_REQUESTED`:

- `CHANGES_REQUESTED` if there is at least one blocking finding.
- `APPROVED` otherwise, even when there are non-blocking notes.

Then:

```markdown
CHANGES_REQUESTED

## Blocking
- `path/to/file.php:42` — <what is wrong>. Why: <bug | ticket mismatch | CLAUDE.md: "<quoted rule>">. Fix: <short suggested fix>.

## Non-blocking
- `path/to/file.ts:10` — <note>.
```

- Cite exact file paths and line numbers from `diff.patch`.
- Report each issue once, even if it appears in several places; list the locations.
- Leave out an empty section. If there are no findings at all, write `APPROVED` followed by `No issues found.`

## Validation pass

A separate run that checks the **blocking findings** of the lenses before they go back to Implement. You did not write these findings; do not trust them.

1. Read the findings file named in the prompt, `diff.patch`, `01-ticket.md`, and `03-qa.md`.
2. For each finding, open the code and check the claim itself: the line exists in the diff, the bug really happens, the ticket really asks for it and `03-qa.md` did not change that, the quoted `CLAUDE.md` rule really exists and applies to that path.
3. Mark it **CONFIRMED** only if you verified it. Mark it **REJECTED** if it is wrong, pre-existing, not blocking under the rules above, or you cannot confirm it.
4. Do not add new findings and do not edit `tests.txt`.

Write the file named in the prompt:

```markdown
CHANGES_REQUESTED

- CONFIRMED `path/to/file.php:42` — <finding in a few words>. <what you checked>.
- REJECTED `path/to/file.ts:10` — <finding in a few words>. <why it is not real or not blocking>.
```

The first line is `CHANGES_REQUESTED` if at least one finding is CONFIRMED, otherwise `APPROVED`.
