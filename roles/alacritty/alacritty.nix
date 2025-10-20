{ config, pkgs, ... }:

{
  # Install Alacritty terminal emulator
  home.packages = with pkgs; [
    alacritty
  ];

  # Link Alacritty configuration
  xdg.configFile."alacritty/alacritty.yml".source = ./configuration/alacritty.yml;
}
