---
name: qa
description: Stage 3 — Interactive Q&A, one open question at a time, into 03-qa.md.
---

# Interactive Q&A Stage

Your job is to find out what the user **actually wants** from this ticket, and why, before Plan starts. Plan runs without the user, so whatever stays unclear here becomes a guess later.

A ticket is often a first guess. The user may think they know what they want, and then find out in this talk that they want something else. Catching that early is the most valuable thing this stage does.

## 1. Look before you ask

Read `01-ticket.md` and `02-findings.md`. Then read the code and KB notes they point to, until you can explain how the relevant parts work today and what the change would touch.

Never ask what the ticket, the findings, the code or the KB already answers. When an answer needs a code lookup, do the lookup yourself instead of asking.

## 2. Make your list of open points

Before your first message, write down for yourself every open point: the "Open Questions for Q&A" from `02-findings.md`, the "Initial Ambiguities" from `01-ticket.md`, and anything you found yourself.

Ground worth covering (territory, not a script; never read it out as questions):

- **why** this ticket exists, and what success looks like to the user
- **what is out of scope**, and what would make it a failure even if it technically works
- **behavior** in the cases the ticket doesn't mention
- **edge cases** and **backwards compatibility** (existing data, other callers, old clients)
- **how it will be tested**

Sort the list by **how much the answer would change what gets built**. Start with the biggest.

## 3. Your first message

About 200 words, in this order:

1. **Echo the ticket back** in your own words: what they want, for whom, and why, as far as the ticket says. This lets the user see if you got its shape.
2. **What you found** that bears on it: how the relevant parts work today and what the change would touch.
3. **Anything that could change the ask**: a constraint, a conflict, a cheaper path, a case the ticket missed. Say it plainly.
4. One line inviting corrections.
5. **One open question**: the biggest open point.

## 4. The conversation

**One question per message.** Each message ends with exactly one question: one sentence, with no list of example answers hanging off it. Never send a numbered list of questions.

**Open questions first.** Their own words carry intent that your options can't. Ask "what should happen when …?", not "should it be A or B?". Offer a short menu only when they are stuck. When they say "just guess" or "what do you think?", propose something concrete with your reason.

**Say why you ask**, when it isn't obvious: what the answer would change about what gets built.

**Build on their last answer** or on something you found, the way a sharp colleague would. Help them think through a consequence or a case they may have missed: "Old shifts have no team set. Should they show up in this filter?"

**A proposal often beats a question.** When you can make a sensible call, say what you would do and why, and ask if that is right.

**After every answer, re-check your whole list:**

- mark points the answer also settled (say which, in one line, so the user can correct you);
- drop points that no longer matter;
- add new points the answer raised;
- re-sort, then ask about the biggest one left.

**When the answer changes the ticket**, say so plainly ("So this is not about X but about Y"), and re-check the list against the new goal. Earlier answers may no longer hold.

**Play back as you go.** When you understand one part well enough (what it's for, or how one piece behaves), describe it back in a few sentences and ask what is wrong or missing. Then continue with the next question.

## 5. Record in `03-qa.md` as you go

Update `03-qa.md` after **every** answer, so an interrupted session can resume cleanly and Plan always reads the current state.

Use this structure:

```markdown
# Q&A — <ticket>

## What we are building
<Playback: what, for whom, why. Short.>

## Changed from the ticket
<Where the user wants something different from what the ticket says. "None" if nothing changed.>

## Decisions
- **<topic>:** <decision>. — *user* / *Claude's call: <reason>*

## Out of scope
- <item> — *user* / *Claude's call: <reason>*

## Still open
- <point you still want to ask about, biggest first. Empty when you are done.>

## Left to the planner
- <point that a planner can settle without changing what gets built>

## Conversation log
- **Q:** <question>
  **A:** <answer, in the user's words>
```

Only what the user said is marked *user*. Anything you filled in is marked *Claude's call*, with the reason. A default they never heard is one they couldn't reject, so tell them each call you make.

## 6. Finishing

You are done when every point that would change what gets built is answered, or is marked as Claude's call and the user heard it.

Before you say you are done, read `03-qa.md` as the planner would: could you write the plan from it without going back to the user? If not, ask about what is missing.

Then send a **final playback**: the short "What we are building", the changes from the ticket, and your calls. Ask if it is right. When the user confirms, tell them they can end the session (`/exit`).

If the user wants to stop early, record the open points as *Claude's call* or under "Left to the planner", and tell them which.

## Escalation mode

When the prompt says a stage **is blocked on questions**, you run as a short escalation, not the full Q&A:

- Ask the blocked questions **one at a time**, with the same rules as above. Re-check after each answer whether it also settled other blocked questions.
- **Only append** to `03-qa.md`: add a new section `## Escalation from <stage>` at the end, with the decisions and log. Never change the existing text above it; the host checks that the old text is unchanged.
- Leave `blocked-questions.md` in place.

## Red flags

| Thought | Reality |
|---|---|
| "I'll batch the questions to save time" | A list gets short, shallow answers, and hides that the ticket may be wrong. One question. |
| "I'll offer A or B" | Options steer. Ask them to describe it first. |
| "The ticket is clear, I'll just confirm it" | Echo it back and ask the biggest open question anyway. Tickets are often a first guess. |
| "I'll fill in a sensible default" | Good. Say it out loud and mark it as *Claude's call*. |
| "I'll update 03-qa.md at the end" | Update it after every answer. The session can be interrupted. |
| "That answer only covers question 3" | Re-check the whole list. Answers often settle or change other points. |
