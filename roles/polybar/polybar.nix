{
  config,
  lib,
  pkgs,
  ...
}:

{
  options.roles.polybar.enable = lib.mkEnableOption "the polybar role";

  config = lib.mkIf config.roles.polybar.enable {
    services.polybar = {
      enable = true;

      # Ensure Polybar is built with i3 and PulseAudio support
      package = pkgs.polybar.override {
        i3Support = true;
        pulseSupport = true;
      };

      # Start the bar automatically
      script = "polybar main &";
    };

    # config.ini and the Win+s toggle script, linked to the repo, not the store.
    # polybar restarts on every i3 reload (Win+Shift+c).
    xdg.configFile."polybar".source =
      config.lib.file.mkOutOfStoreSymlink "${config.dotfiles.path}/roles/polybar/configuration";
  };
}
