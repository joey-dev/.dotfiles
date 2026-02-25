# -----------------------------------------------------------------------------
# USER CUSTOM CONFIGURATION
# -----------------------------------------------------------------------------

# Add Composer global bins and local bins to PATH
export PATH="$HOME/.config/composer/vendor/bin:$HOME/.local/bin:$PATH"

# Auto-start tmux if not already in a tmux session
if [ "$TMUX" = "" ]; then tmux; fi

export TERM=screen
export LANG=en_US.UTF-8

# History formatting
HIST_STAMPS="dd.mm.yyyy"

# Preferred editor logic
if [[ -n $SSH_CONNECTION ]]; then
  export EDITOR='vim'
else
  export EDITOR='nvim'
fi

# -----------------------------------------------------------------------------
# ALIASES
# -----------------------------------------------------------------------------
alias reload="source ~/.zshrc"
alias lla="ls -lah"
alias fuck="eval \$(thefuck \$(fc -ln -1 | tail -n 1)); fc -R" # Proper thefuck integration
alias bat="bat" # Fixed from Ubuntu's 'batcat'
alias whereami="pwd"

# nnn configuration
alias nreload='sh -c "$(curl -Ls https://raw.githubusercontent.com/jarun/nnn/master/plugins/getplugs)"'
export NNN_BMS='h:~;d:~/.dotfiles;s:~/Scripts'
export NNN_PLUG='v:preview-tabbed'
export NNN_INFO="/tmp/nnn.fifo"