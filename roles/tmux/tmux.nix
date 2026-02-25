{ config, pkgs, ... }:

{
  programs.tmux = {
    enable = true;
    shell = "${pkgs.zsh}/bin/zsh";
    extraConfig = builtins.readFile ./configuration/.tmux.conf;
  };

  # Link tmux scripts
  home.file.".config/tmux/tmux-cht.sh" = {
    source = ./configuration/tmux-cht.sh;
    executable = true;
  };
  home.file.".config/tmux/tmux-sessionizer.sh" = {
    source = ./configuration/tmux-sessionizer.sh;
    executable = true;
  };
}
