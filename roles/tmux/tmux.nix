{ config, pkgs, ... }:

{
  # Install tmux
  home.packages = with pkgs; [
    tmux
  ];

  # Link tmux configuration manually
  # We manage the full .tmux.conf file ourselves
  home.file.".tmux.conf".source = ./configuration/.tmux.conf;
  
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
