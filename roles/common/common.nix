{ config, pkgs, ... }:

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
    neofetch
    xclip
    flameshot
    google-chrome
    yazi

    nerd-fonts.comic-shanns-mono
  ];

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
  xdg.configFile."DBeaverData/workspace6/.metadata/.plugins/org.eclipse.core.runtime/.settings/org.jkiss.dbeaver.core.prefs".source = ./configuration/DBeaver.epf;
}
