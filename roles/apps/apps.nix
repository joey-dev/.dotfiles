{
  config,
  lib,
  pkgs,
  ...
}:

{
  options.roles.apps.enable = lib.mkEnableOption "the apps role";

  config = lib.mkIf config.roles.apps.enable {
    home.packages = with pkgs; [
      google-chrome
      libreoffice
    ];

    services.flameshot = {
      enable = true;
      settings = {
        General = {
          useX11LegacyScreenshot = true;
        };
      };
    };
  };
}
