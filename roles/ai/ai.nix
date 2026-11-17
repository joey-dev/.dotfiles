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
        name = "claude-walled";
        runtimeInputs = [ pkgs.bubblewrap ];
        text = builtins.readFile ./configuration/scripts/claude-walled.sh;
      })
    ];

    home.file.".claude" = {
      source = ./configuration/claude;
      recursive = true;
    };

    home.file.".agents/shared" = {
      source = ./configuration/agent-shared;
      recursive = true;
    };

    home.file.".agents/shared/flakes" = {
      source = ../../templates;
      recursive = true;
    };
  };
}
