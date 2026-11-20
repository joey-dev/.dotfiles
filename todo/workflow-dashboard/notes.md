1. if possible, when starting the workflow, start it in the background.
  - need a good way to see all requested active sessions (add it to dashboard of point 5)
  - only when it automatically answers `[c]ontinue` between steps (--auto)
  - starting in a new tmux session

2. make a dashboard
  - see state of all workflows that have not fully finished (finished the retro)
    - easily restart a workflow if it's stopped
  - (point 1) show all workflow requested interactive sessions, where i can easily start them, or connect to them
  - easily open it's workflow folder in nvim:
    1. open new terminal with work directory: ~/.local/state/claude-workflow/{ticket}
    2. run `nvim .`
  - easily open it's worktree folder in nvim:
    1. open new terminal with work directory: /srv/claude-workflow/worktrees/{ticket}
    2. run `nvim .`
  - all my open merge requests + status (comments, pipeline failure, waiting, etc)
    - easily open a merge request in the list on my browser
  - all mr's that requested a review from me
    - easily open a merge request in the list on my browser
  - have a list of all the Jira tickets I'm assigned to
    - can easily open in browser
    - if nothing is currently working on that ticket, I can easily do: start workflow, open with orgastrator, open with new terminal window

# dashboard

made up of widgets
has 1 global dropdown to select the available configs or create a new config

## Jira tickets

## Data from config
- ticket statuses
- user id

### parameters

status: 
  - type: multi-select
  - options: config.jira.statuses
  - default: all

assignee: 
  - type: multi-select
  - options: freefill string + default
  - default: config.jira.user-id



### functionality

shows the:
- ticket name
- assignee
- ticket status
- if something is using it, if yes, what

actions (these are disabled if something is using it):
- start workflow
  - starts new tmux session in background with prefix+ticket-number+timestamp as name, and workDirectory as the root of the repository
  - runs claude_workflow {ticket-number} --auto
- start with orgastrator 
  - starts new tmux session in background with prefix+ticket-number+timestamp as name, and workDirectory as the root of the repository
  - runs claude_orgistrator
- attach to session