{ config, pkgs, lib, ... }:

lib.mkIf pkgs.stdenv.isLinux {

  xsession.windowManager.i3.enable = true;
  services.picom.enable = true;
  services.dunst.enable = true;

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

  xdg.configFile = {
    "i3/config".source = lib.mkForce ./configuration/i3/config;
    
    "i3/scripts".source = ./configuration/scripts;

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