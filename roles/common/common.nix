{
  config,
  lib,
  pkgs,
  ...
}:

{
  options.roles.common.enable = lib.mkEnableOption "the common role";

  config = lib.mkIf config.roles.common.enable {
    fonts.fontconfig.enable = true;

    # Core packages
    home.packages = with pkgs; [
      wget
      curl
      unzip
      htop
      tree
      jq
      fastfetch
      xclip
      google-chrome
      yazi
      libreoffice

      nerd-fonts.comic-shanns-mono
    ];

    services.flameshot = {
      enable = true;
      settings = {
        General = {
          useX11LegacyScreenshot = true;
        };
      };
    };

    # Use native modules for modern CLI tools to auto-inject shell aliases
    programs.eza = {
      enable = true;
      enableZshIntegration = true;
    };

    programs.fzf = {
      enable = true;
      enableZshIntegration = true;
    };

    programs.bat = {
      enable = true;
    };
  };
}
