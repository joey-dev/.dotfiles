{
  config,
  lib,
  pkgs,
  ...
}:

{
  options.roles.i3.enable = lib.mkEnableOption "the i3 role";

  config = lib.mkIf config.roles.i3.enable {
    xsession.windowManager.i3.enable = true;
    services.picom.enable = true;
    services.dunst.enable = true;

    home.packages = with pkgs; [
      i3lock
      dmenu
      rofi
      arandr
      xrandr
      feh
      python3
      pulsemixer
      pavucontrol
      brightnessctl
    ];

    # Media keys; also installs playerctl
    services.playerctld.enable = true;

    # Monitor layouts: `autorandr --save <name>`, then pick one with Win+m
    programs.autorandr.enable = true;

    # Dim the screens after 2 minutes idle, lock 10 seconds later
    services.xidlehook =
      let
        setBrightness =
          value:
          toString (
            pkgs.writeShellScript "set-brightness-${value}" ''
              for display in $(${pkgs.xrandr}/bin/xrandr | ${pkgs.gawk}/bin/awk '/ connected/ {print $1}'); do
                ${pkgs.xrandr}/bin/xrandr --output "$display" --brightness ${value}
              done
            ''
          );
      in
      {
        enable = true;
        not-when-fullscreen = true;
        timers = [
          {
            delay = 120;
            command = setBrightness "0.1";
            canceller = setBrightness "1";
          }
          {
            delay = 10;
            command = "${setBrightness "1"}; ${pkgs.i3lock}/bin/i3lock -c 000000";
          }
        ];
      };

    xdg.configFile = {
      "i3/config".source = lib.mkForce ./configuration/i3/config;

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
      "i3/i3-monitor-menu.sh" = {
        source = ./configuration/i3/i3-monitor-menu.sh;
        executable = true;
      };
    };
  };
}
