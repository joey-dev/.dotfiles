{
  config,
  lib,
  pkgs,
  ...
}:

{
  options.roles.claude.enable = lib.mkEnableOption "the claude role";

  config = lib.mkIf config.roles.claude.enable {
    home.packages = with pkgs; [
      claude-code
      jq
      libnotify
    ];

    home.file.".claude" = {
      source = ./configuration;
      recursive = true;
    };
  };
}
