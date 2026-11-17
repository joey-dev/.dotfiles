{
  config,
  lib,
  pkgs,
  ...
}:

{
  options.roles.ai.enable = lib.mkEnableOption "the ai role";

  config = lib.mkIf config.roles.ai.enable {
    home.packages = with pkgs; [
      claude-code
      codex
      jq
      libnotify
      bubblewrap

      (pkgs.writeShellApplication {
        name = "claude-workflow";
        runtimeInputs = [ pkgs.bubblewrap ];
        text = builtins.readFile ./configuration/scripts/claude-workflow.sh;
      })
    ];

    home.file.".claude" = {
      source = ./configuration/claude;
      recursive = true;
    };
  };
}
