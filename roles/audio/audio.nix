{
  config,
  lib,
  pkgs,
  ...
}:

{
  options.roles.audio.enable = lib.mkEnableOption "the audio role";

  config = lib.mkIf config.roles.audio.enable {
    home.packages = with pkgs; [
      pulsemixer # Win+a
      pavucontrol
    ];
  };
}
