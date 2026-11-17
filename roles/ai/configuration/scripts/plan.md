1. I run a command with a jira ticket as parameter, inside of the root of the repository
2. it checks if the file `$HOME/.agents/docs/{ticketNumber}/currentStep.md` exists. If not create the file, and add the data "Retrieve Ticket". Than go to the step listed

## Step: Retrieve Ticket
1. retrieve the ticket, and add all it's information inside of: `$HOME/.agents/docs/{ticketNumber}/retrieved/ticket.md`
2. go to step: Setup

## Step: Setup
1. create a new directory: `$HOME/.agents/sandboxes/{ticketNumber}`
2. inside that directory, add directory: `docs`, `info`, `home`, and `{repositoryName}`
3. create a new worktree from the main branch (likely master), with the branch name `{ticketNumber}`, and pointing to the new directory (`$HOME/.agents/sandboxes/{ticketNumber}/{$repositoryName}`)

## Bwrap defaults
  - no internet access
  - (home) bind: `$HOME/.agents/sandboxes/{ticketNumber}/home` to `$HOME`
  - (repo) bind: `$HOME/.agents/sandboxes/{ticketNumber}/{$repositoryName}` to `$HOME/{$repositoryName}`
  - (info) bind: `$HOME/.agents/docs/{ticketNumber}/retrieved/` to `$HOME/info`
  - (plan-docs) bind: `$HOME/.agents/docs/{ticketNumber}/docs/plan` to `$HOME/plan-docs`
  - (write-docs) bind: `$HOME/.agents/docs/{ticketNumber}/docs/write` to `$HOME/write-docs`
  - (review-docs) bind: `$HOME/.agents/docs/{ticketNumber}/docs/review` to `$HOME/review-docs`
  - (currentStep) ro-bind: `$HOME/.agents/docs/{ticketNumber}/currentStep.md` to `$HOME/currentStep.md`
  - (flake) ro-bind: `$HOME/.agents/shared/flakes/latest` to `$HOME/flake/`
  - (skills) ro-bind: `$HOME/.agents/shared/skills/` to `$HOME/.claude/skills/`
  - (agents) ro-bind: `$HOME/.agents/shared/agents/` to `$HOME/.claude/agents/`
  - (credentials) copy: `$HOME/.claude/.credentials.json` to `$HOME/.agents/sandboxes/{ticketNumber}/home/.claude/.credentials.json`

## Step: Brainstorming
1. create new bwrap, but overwrite:
  - has internet access
  - ro-bind for: write-docs, review-docs, repo, info
2. within brwap, call claude with flake
3. call skill `brainstorming`, write all it's details in `plan-docs`, and have all it's questions at the bottom
  - might want to change the questions to be interactive, so in the chat

## Step: Plan
1. create new bwrap, but overwrite:
  - has internet access
  - ro-bind for: write-docs,  review-docs,repo, info
2. within brwap, call claude with flake
3. call skill `write-plan`, write all it's details in `plan-docs`, and have all it's questions at the bottom

## Step: validate
1. create new bwrap, but overwrite:
  - has internet access
  - ro-bind for: write-docs, review-docs, repo, info
2. within brwap, call claude with flake
3. call skill `validate-plan`, it should go over all the `plan-docs`, and figure out if we are missing things. it can decide which questions to answer himself, or which questions it needs to ask me

## Step: execute
1. create new bwrap, but overwrite:
  - ro-bind for: plan-docs, review-docs, info
2. within brwap, call claude with flake
3. call skill `execute-plan`

## Step: review
1. create new bwrap, but overwrite:
  - ro-bind for: plan-docs, write-docs, repo, info
2. within brwap, call claude with flake
3. call skill `review`
4. if any points to improve, go back to execute

## Step: done
1. let me know that it's done, and ready for review (local)


## good to know
- first, between every step, I want to confirm it. this way it's easier to see when something is off, and we can try to fix it
- it can not push changes, but it can commit (fixed using read-only script, that host executes)
- there is a log, that's updated between steps. this way we can follow things back for improvements
  - also when validation spotted something, ask why it was not spotted earlier.
