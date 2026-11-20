1. twice?
```
[intake] [c]ontinue / [r]etry stage / [a]bort: [intake] [c]ontinue / [r]etry stage / [a]bort: c
```
- only happened the first step (when it finished intake)
- TODO. test once more for the first step. might be because i was doing other things at the same time

2. it should say that i need to type ``/exit`. if possible automatically, but manual is fine
```
● Close that chat with /exit, and don't answer "yes". The script then moves on to the plan stage by itself.

  Reasoning

  - The workflow starts the Q&A chat and waits until that chat process ends (stages/qa.py:52, claude_runner.py:182). It does not watch what you type in the
    chat.
  - When the chat exits with code 0, the script checks 03-qa.md. It then shows its approval gate and starts Plan in a new, separate session with its own
    sandbox and prompt.
  - If you answer "yes", the Q&A session writes the plan itself, outside the Plan stage. The real Plan stage would then run again anyway.
  - Don't use Ctrl-C. It gives exit code 130, so the stage counts as FAILED. It can be resumed, but that's messy. /exit (or Ctrl-D) gives a clean exit.

  What to do

  1. Type /exit in that chat.
  2. The script asks you to approve the Q&A result. Approve it, and the Plan stage starts.


  Small improvement for later (in your skills worktree)

  The Q&A Claude doesn't know it should tell you to exit. Its prompt or skill could end with: "When all questions are answered, tell the user to type /exit so
  the workflow continues." I won't change it now, because you're working on the skills in ~/improve-workflow-skills.
```

3. if possible, when starting the workflow, start it in the background.
  - need a good way to see all requested active sessions (add it to dashboard of point 5)
  - only when it automatically answers `[c]ontinue` between steps (--auto)

4. phpstan error on changed files
```
- `phpstan` (default config) on the changed application files: clean for the `Newsfeed` directories. When run on `BaseController.php` alone it reports `Function t not found` at line 186. That line is not part of my change, and I did not run the full-project analysis.
```
```

```text
$ vendor/bin/phpstan analyze Component/CommunicationCenter/Infrastructure/Newsfeed/DefaultNewsfeedPostLinkFallbackResolver.php Component/CommunicationCenter/Presentation/Newsfeed/InteractableLocationUrlsProvider.php Component/CommunicationCenter/Presentation/Newsfeed/NewsfeedController.php Component/CommunicationCenter/Presentation/Newsfeed/NewsfeedPostLinkFallbackResolver.php Component/CommunicationCenter/Presentation/Newsfeed/OfficeQueryInteractableLocationUrlsProvider.php app/classes/Controller/BaseController.php app/classes/Infrastructure/Authentication/AuthenticationService.php --memory-limit=-1 --no-progress -c phpstan.neon.dist
 ------ --------------------------------------------------------------------- 
  Line   app/classes/Controller/BaseController.php                            
 ------ --------------------------------------------------------------------- 
  186    Function t not found.                                                
         🪪  function.notFound                                                
         💡 Learn more at https://phpstan.org/user-guide/discovering-symbols  
 ------ --------------------------------------------------------------------- 


 [ERROR] Found 1 error
```

5. make a sort of dashboard
  - see state of all workflows that have not fully finished (finished the retro)
    - easily restart a workflow if it's stopped
  - (point 3) show all workflow requested interactive sessions, where i can easily start them, or connect to them
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

6. it shouldn't have deleted this file. as it errors out (correctly) in the verify step
  - `        deleted:    nginx-proxy/certs/.gitkeep`

7. when it starts the verify stage, it should immidiatly check if the stack is already up, instead of later
```
Error response from daemon: failed to set up container networking: driver failed programming external connectivity on endpoint dyflexis-monorepo-db-1 (14b0c0b28a900f381fc89637ebac2e836d488a58c1f19470b7ee23fd34648ba2): error while calling RootlessKit PortManager.AddPort(): listen tcp4 0.0.0.0:3306: bind: address already in use
Hint: a host port is taken (a dev stack on :80/:443?). Please stop your dev stack and try again.
```

8. stack should do down, and force-recreate (maybe already written down by claude)
```
  - After a failed up, the workflow should clean up. Run down on failure, or use up --force-recreate. Otherwise the next Verify reuses broken containers. I'll
    add this to the plan 13 results.
```


