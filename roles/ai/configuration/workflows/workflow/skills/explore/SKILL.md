---
name: explore
description: Stage 2 — Read-only mono-repo and KB exploration into 02-findings.md.
---

# Explore Stage

Your findings feed the Q&A stage. There, Claude echoes the ticket back to the user, says what you found, and asks the open questions one at a time, **biggest first**. Write `02-findings.md` so Q&A can do that without re-reading the whole repo.

1. Read `01-ticket.md` and relevant notes in the Personal KB (read-only).
2. Locate the relevant modules, entrypoints, existing tests, and legacy quirks in the repository. Keep reading until you can explain **how the relevant parts work today** and **what this change would touch**.
3. Look for anything that could change what the ticket asks for: an existing feature that already does most of it, a constraint, a conflict with other code, or a cheaper path. A ticket is often a first guess, so this matters more than a complete file list.
4. Write `02-findings.md` with:
   - **How It Works Today**: a few sentences on the current behavior, and what the change would touch.
   - **Could Change the Ticket**: what you found in step 3, each with the file that shows it. "None found" if nothing.
   - **Relevant Files & Symbols**
   - **Existing Patterns & Helpers to Reuse**
   - **Legacy Quirks / Risks**
   - **Open Questions for Q&A**: sorted by how much the answer would change what gets built, biggest first. Leave out anything the code, the ticket or the KB already answers.
