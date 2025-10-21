{ config, pkgs, lib, ... }:

{
  # Install i3 window manager and related tools
  # Only install i3 and X-related packages on NixOS
  home.packages = with pkgs; lib.mkIf pkgs.stdenv.isLinux [
    i3
    i3status
    i3lock
    dmenu
    rofi
    arandr  # GUI for xrandr
    xorg.xrandr
    autorandr
    feh  # For setting wallpapers
    picom  # Compositor
    dunst  # Notification daemon
    
    # Python for i3 scripts
    python3
  ];

  # Link i3 configuration
  xdg.configFile."i3/config".source = ./configuration/i3/config;
  
  # Link i3 scripts
  xdg.configFile."i3/i3-move-display.sh" = {
    source = ./configuration/i3/i3-move-display.sh;
    executable = true;
  };
  xdg.configFile."i3/i3-power-settings.sh" = {
    source = ./configuration/i3/i3-power-settings.sh;
    executable = true;
  };
  xdg.configFile."i3/i3-swap-display.sh" = {
    source = ./configuration/i3/i3-swap-display.sh;
    executable = true;
  };

  # Link scripts directory
  home.file.".config/i3/scripts".source = ./configuration/scripts;
}
