{ pkgs, ... }:

{
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

  # Link DBeaver configuration
  xdg.configFile."DBeaverData/workspace6/.metadata/.plugins/org.eclipse.core.runtime/.settings/org.jkiss.dbeaver.core.prefs".source =
    ./configuration/DBeaver.epf;
}
