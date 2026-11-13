AGENT_NAME="$(basename "$PWD")"
SANDBOX_HOME="$HOME/.claude-sandboxes/$AGENT_NAME"
CLAUDE_BIN="$(readlink -f "$(command -v claude)")"
NIX_PROFILE_DIR="$(readlink -f "$HOME/.nix-profile")"

mkdir -p "$SANDBOX_HOME/.claude/skills" "$SANDBOX_HOME/.claude/agents"

exec bwrap \
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
  --bind "$SANDBOX_HOME" "$HOME" \
  --ro-bind-try "$NIX_PROFILE_DIR" "$HOME/.nix-profile" \
  --ro-bind "$HOME/.claude-shared/skills" "$HOME/.claude/skills" \
  --ro-bind "$HOME/.claude-shared/agents" "$HOME/.claude/agents" \
  --bind "$PWD" "$PWD" \
  --chdir "$PWD" \
  --setenv PATH "$PATH" \
  --unshare-pid \
  --die-with-parent \
  "$CLAUDE_BIN" "$@"
