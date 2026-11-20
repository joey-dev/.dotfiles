1. if possible, when starting the workflow, start it in the background.
  - need a good way to see all requested active sessions (add it to dashboard of point 5)
  - only when it automatically answers `[c]ontinue` between steps (--auto)

2. make a sort of dashboard
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
  - maybe more?
