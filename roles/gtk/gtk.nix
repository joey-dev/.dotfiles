{ config, pkgs, ... }:

{
  # GTK theme and icon theme configuration
  gtk = {
    enable = true;
    theme = {
      name = "Adwaita-dark";
      package = pkgs.gnome.gnome-themes-extra;
    };
    iconTheme = {
      name = "Adwaita";
      package = pkgs.gnome.adwaita-icon-theme;
    };
  };

  # Link GTK configuration files
  xdg.configFile."gtk-3.0/settings.ini".source = ./configuration/gtk-3.0/settings.ini;
  xdg.configFile."gtk-4.0/settings.ini".source = ./configuration/gtk-4.0/settings.ini;
}
