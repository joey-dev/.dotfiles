#!/usr/bin/env bash
set -euo pipefail

fail() {
  printf 'claude-walled: %s\n' "$*" >&2
  exit 1
}

[[ $# == 2 && -n $1 && -n $2 ]] || fail 'Usage: claude-walled.sh <branch|bash> <goal>'
for required in git nix bwrap readlink basename mkdir chmod install; do
  command -v "$required" >/dev/null || fail "Required command not found: $required"
done
if [[ $1 != bash ]]; then
  command -v claude >/dev/null || fail 'Required command not found: claude'
fi
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || fail 'Run inside a Git working tree'
REPOSITORY_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPOSITORY_ROOT"
git check-ref-format --branch "$1" >/dev/null 2>&1 || fail "Invalid branch: $1"
[[ $1 != -* && $1 != HEAD && $1 != @* ]] || fail "Invalid branch: $1"
git remote get-url origin >/dev/null 2>&1 || fail 'Repository has no origin remote'

BRANCH="$1"
GOAL="$2"
SAFE_NAME="${BRANCH//\//-}"
REPOSITORY_NAME="$(basename "$PWD")"

CLAUDE_BIN=''
if [[ $BRANCH != bash ]]; then
  CLAUDE_BIN="$(readlink -f "$(command -v claude)")"
fi

MAIN_SANDBOX_HOME="$HOME/.agents/sandboxes/$REPOSITORY_NAME/$SAFE_NAME"
AGENT_SANDBOX_HOME="$HOME"

MAIN_SANDBOX_NOTES="$HOME/.agents/notes/$REPOSITORY_NAME/$SAFE_NAME"
AGENT_SANDBOX_NOTES="$HOME/notes"

MAIN_WORKTREE_DIR="$MAIN_SANDBOX_HOME/$REPOSITORY_NAME"
AGENT_WORKTREE_DIR="$HOME/$REPOSITORY_NAME"

MAIN_NIX_PROFILE_DIR="$(readlink -f "$HOME/.nix-profile")"
AGENT_NIX_PROFILE_DIR="$HOME/.nix-profile"

MAIN_FLAKE_DIR="$HOME/.agents/shared/flakes/latest"
AGENT_FLAKE_DIR="$HOME/flake"

MAIN_SKILLS_DIR="$HOME/.agents/shared/skills"
AGENT_SKILLS_DIR="$HOME/.claude/skills"

MAIN_AGENTS_DIR="$HOME/.agents/shared/agents"
AGENT_AGENTS_DIR="$HOME/.claude/agents"

MAIN_CREDENTIALS="$HOME/.claude/.credentials.json"
SANDBOX_CREDENTIALS="$MAIN_SANDBOX_HOME/.claude/.credentials.json"

SYSTEM_PROMPT="Goal: $GOAL. Keep all your notes/docs inside of $AGENT_SANDBOX_NOTES"

for shared_dir in "$MAIN_FLAKE_DIR" "$MAIN_SKILLS_DIR" "$MAIN_AGENTS_DIR"; do
  [[ -d $shared_dir && -r $shared_dir && -x $shared_dir ]] || fail "Shared directory unavailable: $shared_dir"
done
[[ -r $MAIN_FLAKE_DIR/flake.nix ]] || fail "Missing flake: $MAIN_FLAKE_DIR/flake.nix"
[[ ! -L $SANDBOX_CREDENTIALS ]] || fail 'Sandbox credentials must not be a symlink'
if [[ -e $SANDBOX_CREDENTIALS ]]; then
  [[ -f $SANDBOX_CREDENTIALS && -r $SANDBOX_CREDENTIALS && ! -L $SANDBOX_CREDENTIALS ]] || fail 'Sandbox credentials must be a readable regular file'
else
  [[ -f $MAIN_CREDENTIALS && -r $MAIN_CREDENTIALS ]] || fail "Missing host credentials: $MAIN_CREDENTIALS"
fi

RESUME=false
if [[ -e $MAIN_WORKTREE_DIR || -L $MAIN_WORKTREE_DIR ]]; then
  [[ -d $MAIN_WORKTREE_DIR && ! -L $MAIN_WORKTREE_DIR ]] || fail "Worktree path is occupied: $MAIN_WORKTREE_DIR"
  EXPECTED_COMMON="$(git rev-parse --path-format=absolute --git-common-dir)"
  ACTUAL_COMMON="$(git -C "$MAIN_WORKTREE_DIR" rev-parse --path-format=absolute --git-common-dir 2>/dev/null)" || fail 'Existing path is not a Git worktree'
  ACTUAL_ROOT="$(git -C "$MAIN_WORKTREE_DIR" rev-parse --show-toplevel)"
  ACTUAL_BRANCH="$(git -C "$MAIN_WORKTREE_DIR" symbolic-ref --quiet --short HEAD)" || fail 'Existing worktree has a detached HEAD'
  [[ $ACTUAL_COMMON == "$EXPECTED_COMMON" && $ACTUAL_ROOT == "$MAIN_WORKTREE_DIR" && $ACTUAL_BRANCH == "$BRANCH" ]] || fail 'Existing path belongs to a different repository or branch'
  RESUME=true
fi
while IFS= read -r -d '' worktree_field; do
  if [[ $worktree_field == "branch refs/heads/$BRANCH" && $RESUME == false ]]; then
    fail "Branch is already checked out in another worktree: $BRANCH"
  fi
done < <(git worktree list --porcelain -z)

if [[ $BRANCH == bash ]] || { [[ $RESUME == false ]] && ! git show-ref --verify --quiet "refs/heads/$BRANCH"; }; then
  REMOTE_HEAD="$(git ls-remote --symref origin HEAD)"
  DEFAULT_REF=''
  while read -r marker remote_ref head_ref; do
    if [[ $marker == ref: && $head_ref == HEAD ]]; then
      DEFAULT_REF=$remote_ref
      break
    fi
  done <<< "$REMOTE_HEAD"
  [[ $DEFAULT_REF == refs/heads/* ]] || fail 'Cannot determine origin default branch'
  git fetch origin "$DEFAULT_REF"
  BASE_COMMIT="$(git rev-parse --verify FETCH_HEAD^{commit})"
fi

mkdir -p \
  "$MAIN_SANDBOX_NOTES" \
  "$MAIN_SANDBOX_HOME/.claude/skills" \
  "$MAIN_SANDBOX_HOME/.claude/agents"

chmod 700 "$MAIN_SANDBOX_HOME/.claude" || exit 1
if [[ ! -e $SANDBOX_CREDENTIALS ]]; then
  install -m 600 "$MAIN_CREDENTIALS" "$SANDBOX_CREDENTIALS" || exit 1
fi
chmod 600 "$SANDBOX_CREDENTIALS" || exit 1

if [[ $BRANCH == "bash" ]]; then
  if [[ $RESUME == true ]]; then
    git worktree remove --force "$MAIN_WORKTREE_DIR" || exit 1
  fi
  git worktree add "$MAIN_WORKTREE_DIR" -B "$BRANCH" "$BASE_COMMIT" || exit 1
elif [[ $RESUME == false ]]; then
  if git show-ref --verify --quiet "refs/heads/$BRANCH"; then
    git worktree add "$MAIN_WORKTREE_DIR" "$BRANCH"
  else
    git worktree add "$MAIN_WORKTREE_DIR" -b "$BRANCH" "$BASE_COMMIT"
  fi
fi

if [[ $1 == "bash" ]]; then
  AGENT=(bash)
else
  AGENT=(
    "$CLAUDE_BIN"
    --system-prompt "$SYSTEM_PROMPT"
    --name "$SAFE_NAME"
    --add-dir "$AGENT_SANDBOX_NOTES"
    --add-dir "$AGENT_WORKTREE_DIR"
    --add-dir "$AGENT_FLAKE_DIR"
    --permission-mode bypassPermissions
    "Ask me up to 3 clarifying questions before editing any files."
  )
fi

cd "$MAIN_WORKTREE_DIR"
exec nix develop "$MAIN_FLAKE_DIR" --command \
  bwrap \
  --ro-bind /nix/store /nix/store \
  --ro-bind-try /run/current-system /run/current-system \
  --ro-bind-try /etc/profiles /etc/profiles \
  --ro-bind-try /etc/static /etc/static \
  --ro-bind-try /bin /bin \
  --ro-bind-try /usr /usr \
  --ro-bind /etc/resolv.conf /etc/resolv.conf \
  --ro-bind /etc/ssl /etc/ssl \
  --ro-bind /etc/hosts /etc/hosts \
  --proc /proc \
  --dev /dev \
  --tmpfs /tmp \
  --tmpfs /home \
  --bind "$MAIN_SANDBOX_HOME" "$AGENT_SANDBOX_HOME" \
  --ro-bind-try "$MAIN_NIX_PROFILE_DIR" "$AGENT_NIX_PROFILE_DIR" \
  --ro-bind "$MAIN_SKILLS_DIR" "$AGENT_SKILLS_DIR" \
  --ro-bind "$MAIN_AGENTS_DIR" "$AGENT_AGENTS_DIR" \
  --ro-bind "$MAIN_FLAKE_DIR" "$AGENT_FLAKE_DIR" \
  --bind "$MAIN_SANDBOX_NOTES" "$AGENT_SANDBOX_NOTES" \
  --bind "$PWD" "$PWD" \
  --chdir "$PWD" \
  --setenv PATH "$PATH" \
  --unshare-pid \
  --die-with-parent \
  "${AGENT[@]}"
