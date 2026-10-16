{
  config,
  lib,
  pkgs,
  ...
}:

{
  options.roles.fonts.enable = lib.mkEnableOption "the fonts role";

  config = lib.mkIf config.roles.fonts.enable {
    fonts.fontconfig.enable = true;

    home.packages = with pkgs; [
      nerd-fonts.comic-shanns-mono
    ];
  };
}
