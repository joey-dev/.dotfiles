{ config, pkgs, ... }:

{
  # Install tmux and related tools
  home.packages = with pkgs; [
    tmux
  ];

  # Tmux configuration using home-manager
  programs.tmux = {
    enable = true;
    # Additional tmux configuration will be loaded from .tmux.conf
  };

  # Link tmux configuration
  home.file.".tmux.conf".source = ./configuration/.tmux.conf;
  home.file.".bashrc".source = ./configuration/.bashrc;
  
  # Link tmux scripts
  home.file.".local/bin/tmux-cht.sh" = {
    source = ./configuration/tmux-cht.sh;
    executable = true;
  };
  home.file.".local/bin/tmux-sessionizer.sh" = {
    source = ./configuration/tmux-sessionizer.sh;
    executable = true;
  };
}
