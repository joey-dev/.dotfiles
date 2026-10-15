{
  config,
  lib,
  pkgs,
  ...
}:

{
  options.roles.ghostty.enable = lib.mkEnableOption "the ghostty role";

  config = lib.mkIf config.roles.ghostty.enable {
    home.packages = with pkgs; [
      ghostty
    ];

    # The missing link! This tells Nix to actually use our config file.
    xdg.configFile."ghostty/config".source = ./configuration/config;
  };
}
