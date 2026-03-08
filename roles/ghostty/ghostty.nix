{ pkgs, ... }:

{
  home.packages = with pkgs; [
    ghostty
  ];

  # The missing link! This tells Nix to actually use our config file.
  xdg.configFile."ghostty/config".source = ./configuration/config;
}
