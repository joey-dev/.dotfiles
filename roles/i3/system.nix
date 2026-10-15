{
  config,
  lib,
  pkgs,
  username,
  ...
}:

{
  config = lib.mkIf config.roles.i3.enable {
    services.xserver = {
      enable = true;

      displayManager.lightdm.enable = true;

      # Defer to Home Manager for the window manager
      desktopManager.runXdgAutostartIfNone = true;

      # System-level fallback, so LightDM offers an i3 session
      windowManager.i3.enable = true;
    };

    # Lets the video group change the backlight with brightnessctl
    services.udev.packages = [ pkgs.brightnessctl ];
    users.users.${username}.extraGroups = [ "video" ];
  };
}
