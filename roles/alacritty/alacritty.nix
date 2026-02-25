{ config, pkgs, ... }:

{
  programs.alacritty.enable = true;

  # Link Alacritty configuration
  xdg.configFile."alacritty/alacritty.yml".source = ./configuration/alacritty.yml;
}
