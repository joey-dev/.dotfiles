# -----------------------------------------------------------------------------
# USER CUSTOM CONFIGURATION
# -----------------------------------------------------------------------------

export PATH="$HOME/.config/composer/vendor/bin:$HOME/.local/bin:$PATH"

if [ "$TMUX" = "" ]; then tmux; fi

export TERM=screen
export LANG=en_US.UTF-8
HIST_STAMPS="dd.mm.yyyy"

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
alias bat="bat" 
alias whereami="pwd"

eval "$(pay-respects zsh --alias fuck)"

# nnn configuration
# nreload: removed — on NixOS, nnn plugins must be managed declaratively via programs.nnn or home.packages
export NNN_BMS='h:~;d:~/.dotfiles;s:~/Scripts'
export NNN_PLUG='v:preview-tabbed'
export NNN_INFO="/tmp/nnn.fifo"