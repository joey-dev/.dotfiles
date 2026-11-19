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
- If you think a test will fail, append it to `tests.txt` under `# suggested by review` and report it as a finding. Do not change anything else in `tests.txt`.


1. Launch a sonnet agent to view the pull request and return a summary of the changes

2. Launch 4 agents in parallel to independently review the changes. Each agent should return the list of issues, where each issue includes a description and the reason it was flagged (e.g. "CLAUDE.md adherence", "bug"). The agents should do the following:
   Agents 1 + 2: CLAUDE.md compliance sonnet agents
   Audit changes for CLAUDE.md compliance in parallel. Note: When evaluating CLAUDE.md compliance for a file, you should only consider CLAUDE.md files that share a file path with the file or parents.
   Agent 3: Opus bug agent (parallel subagent with agent 4)
   Scan for obvious bugs. Focus only on the diff itself without reading extra context. Flag only significant bugs; ignore nitpicks and likely false positives. Do not flag issues that you cannot validate without looking at context outside of the git diff.
   Agent 4: Opus bug agent (parallel subagent with agent 3)
   Look for problems that exist in the introduced code. This could be security issues, incorrect logic, etc. Only look for issues that fall within the changed code.
   **CRITICAL: We only want HIGH SIGNAL issues.** Flag issues where:
   - The code will fail to compile or parse (syntax errors, type errors, missing imports, unresolved references)
   - The code will definitely produce wrong results regardless of inputs (clear logic errors)
   - Clear, unambiguous CLAUDE.md violations where you can quote the exact rule being broken
   Do NOT flag:
   - Code style or quality concerns
   - Potential issues that depend on specific inputs or state
   - Subjective suggestions or improvements
   If you are not certain an issue is real, do not flag it. False positives erode trust and waste reviewer time.
   In addition to the above, each subagent should be told the PR title and description. This will help provide context regarding the author's intent.

3. For each issue found in the previous step by agents 3 and 4, launch parallel subagents to validate the issue. These subagents should get the PR title and description along with a description of the issue. The agent's job is to review the issue to validate that the stated issue is truly an issue with high confidence. For example, if an issue such as "variable is not defined" was flagged, the subagent's job would be to validate that is actually true in the code. Another example would be CLAUDE.md issues. The agent should validate that the CLAUDE.md rule that was violated is scoped for this file and is actually violated. Use Opus subagents for bugs and logic issues, and sonnet agents for CLAUDE.md violations.

4. Filter out any issues that were not validated in step 5. This step will give us our list of high signal issues for our review.

5. Output a summary of the review findings to the terminal:
   - If issues were found, list each issue with a brief description.
   - If no issues were found, state: "No issues found. Checked for bugs and CLAUDE.md compliance."
   If `--comment` argument was NOT provided, stop here. Do not post any GitHub comments.
   If `--comment` argument IS provided and NO issues were found, post a summary comment using `gh pr comment` and stop.
   If `--comment` argument IS provided and issues were found, continue to step 8.

6. Create a list of all comments that you plan on leaving. This is only for you to make sure you are comfortable with the comments. Do not post this list anywhere.

7. for each issue:
   - Provide a brief description of the issue
   - For small, self-contained fixes, include a committable suggestion block
   - For larger fixes (6+ lines, structural changes, or changes spanning multiple locations), describe the issue and suggested fix without a suggestion block
   **IMPORTANT: Only comment per unique issue. Do not post duplicate comments.**
Use this list when evaluating issues in Steps 4 and 5 (these are false positives, do NOT flag):

      - Pre-existing issues
      - Something that appears to be a bug but is actually correct
      - Pedantic nitpicks that a senior engineer would not flag
      - Issues that a linter will catch (do not run the linter to verify)
      - General code quality concerns (e.g., lack of test coverage, general security issues) unless explicitly required in CLAUDE.md
      - Issues mentioned in CLAUDE.md but explicitly silenced in the code (e.g., via a lint ignore comment)


