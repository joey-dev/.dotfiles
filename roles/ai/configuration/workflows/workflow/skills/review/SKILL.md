---
name: review
description: Stage 7 — Adversarial read-only code review over diff.patch.
---

# Automated Code Review Stage

Adopt the mindset that **someone else wrote this code** and you are reviewing their MR:
- **Correctness lens:** Look for logic bugs, unhandled edge cases, regressions, and missing tests.
- **Conventions lens:** Look for departures from repo style, duplicated logic, unclear naming, or unnecessary complexity.
- Cite exact file paths and line numbers from `diff.patch`. Skip trivial bike-shedding.
- Start each lens report with `CHANGES_REQUESTED` if a finding blocks acceptance, or `APPROVED` if the change can proceed.
