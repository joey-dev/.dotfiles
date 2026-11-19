---
name: retro
description: Stage 8 — Human check-in and proposed diffs to skills or Personal KB.
---

# Human Check & Retro Stage

1. Summarize `06-verify.md` and `07-review.md` for the user. Lead with what matters most; offer the rest.
2. **Show the calls nobody confirmed.** Collect every *Claude's call*, *planner's call* and *implementer's call* from `03-qa.md`, `04-plan.md` and `05-implement.md`. List them briefly, so the user can check those first. Also check the diff against the "Changed from the ticket" section of `03-qa.md`.
3. Capture human review feedback and surprises encountered in the legacy codebase. Ask **one open question at a time**, building on the last answer. After each answer, check whether it also covered other points.
4. Propose concrete, minimal diffs to the Personal KB or stage `SKILL.md` files in `08-retro.md`. Never apply KB edits without explicit user approval.
   - Base each proposal on something the user said or something you can point to in the notes or diff. Mark which: *user* or *observed in <file>*.
   - Prefer proposals that would have caught a problem earlier: a question Q&A should have asked, a finding Explore missed, a call that should have gone to the user.
