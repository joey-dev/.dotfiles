{ config, pkgs, lib, ... }:

# Wrap the entire configuration in mkIf so none of this evaluates on macOS/Darwin
lib.mkIf pkgs.stdenv.isLinux {

  # 1. Use native Home Manager modules for your core services
  xsession.windowManager.i3.enable = true;
  services.picom.enable = true;
  services.dunst.enable = true;

  # 2. Install supplementary packages
  home.packages = with pkgs; [
    i3status
    i3lock
    dmenu
    rofi
    arandr
    xorg.xrandr
    autorandr
    feh
    python3
  ];

  # 3. Consolidate file linking using xdg.configFile consistently
  xdg.configFile = {
    # Link the main config
    "i3/config".source = ./configuration/i3/config;
    
    # Link the entire scripts directory cleanly
    "i3/scripts".source = ./configuration/scripts;

    # Link specific executable scripts
    "i3/i3-move-display.sh" = {
      source = ./configuration/i3/i3-move-display.sh;
      executable = true;
    };
    "i3/i3-power-settings.sh" = {
      source = ./configuration/i3/i3-power-settings.sh;
      executable = true;
    };
    "i3/i3-swap-display.sh" = {
      source = ./configuration/i3/i3-swap-display.sh;
      executable = true;
    };
  };
}