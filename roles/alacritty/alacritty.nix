{ config, pkgs, ... }:

{
  programs.alacritty.enable = true;

  # Link Alacritty configuration
  xdg.configFile."alacritty/alacritty.toml".source = ./configuration/alacritty.toml;
}
