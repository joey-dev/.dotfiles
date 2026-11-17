# claude-walled follow-ups

- [x] Validate arguments and prerequisites before creating directories or fetching.
  Check required commands, shared directories, credentials, and repository state.
  Avoid assuming every repository has `origin/master` or that local `master` can
  be updated while checked out. Add a resume path for existing branches and
  worktrees outside the disposable `bash` test mode.
- [ ] Support Nix commands inside the sandbox on daemon-based installations.
  The initial `nix develop` runs outside the sandbox, but `/nix/store` alone
  does not provide daemon access for subsequent `nix shell` or builds. Decide
  how to expose the daemon socket and required state within the sandbox.


- [ ] Host Git & Compose Socket Broker (host-broker)
  - basically, if claude wants to run commands/retrieve information, it can only do that using script(s) that validate input and call it from outside
  - On your host, host-broker listens on /tmp/claude-broker-<worktree>.sock (which you mount into bwrap via --bind).
  - Inside the sandbox, Claude runs a tiny read-only client (worktree-ctl diff, worktree-ctl add src/File.php, or worktree-ctl commit).
  - The host validates the path (blocking .. or flags starting with -), runs git commit with the current branch name as the message, and blocks all branch switching.
  - Git socket only allows git status, git diff, git add <file>, and git commit (for now atleast)
  - we will also add other commands later

