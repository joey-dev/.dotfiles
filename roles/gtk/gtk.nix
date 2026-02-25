{ config, pkgs, ... }:

{
  # Install GTK theme packages
  home.packages = with pkgs; [
    gnome-themes-extra
    adwaita-icon-theme
  ];

  # Link GTK configuration files manually
  # We manage the full settings.ini files ourselves
  xdg.configFile."gtk-3.0/settings.ini".source = ./configuration/gtk-3.0/settings.ini;
  xdg.configFile."gtk-4.0/settings.ini".source = ./configuration/gtk-4.0/settings.ini;
}
