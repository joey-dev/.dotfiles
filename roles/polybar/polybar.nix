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

      # Load our config file
      extraConfig = builtins.readFile ./configuration/config.ini;
    };
  };
}
