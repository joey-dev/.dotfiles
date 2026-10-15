{
  config,
  lib,
  pkgs,
  ...
}:

{
  options.roles.tmux.enable = lib.mkEnableOption "the tmux role";

  config = lib.mkIf config.roles.tmux.enable {
    programs.tmux = {
      enable = true;
      shell = "${pkgs.zsh}/bin/zsh";
      extraConfig = builtins.readFile ./configuration/.tmux.conf;
    };

    # Link tmux scripts
    home.file.".config/tmux/tmux-sessionizer.sh" = {
      source = ./configuration/tmux-sessionizer.sh;
      executable = true;
    };
  };
}
