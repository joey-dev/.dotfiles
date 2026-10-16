{
  config,
  lib,
  pkgs,
  ...
}:

{
  options.roles.i3.enable = lib.mkEnableOption "the i3 role";

  config = lib.mkIf config.roles.i3.enable {
    # i3 itself is installed by ./system.nix. The Home Manager i3 module is not used,
    # because it writes i3/config itself and the folder below is linked as a whole.
    services.picom.enable = true;
    services.dunst.enable = true;

    home.packages = with pkgs; [
      i3lock
      arandr
      xrandr
      feh
      brightnessctl
    ];

    # App launcher (Win+d) and the menus of the i3 scripts
    programs.rofi.enable = true;

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

    # Linked to the repo, not the store: edit, then Win+Shift+c to reload
    xdg.configFile."i3".source =
      config.lib.file.mkOutOfStoreSymlink "${config.dotfiles.path}/roles/i3/configuration/i3";
  };
}
