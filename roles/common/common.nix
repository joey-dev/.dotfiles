{ config, pkgs, ... }:

{
  # Common system utilities and tools
  home.packages = with pkgs; [
    # System utilities
    wget
    curl
    unzip
    htop
    tree
    jq
    
    # Additional tools
    fzf
    bat
    eza
    
    # System monitoring
    neofetch
    
    # Clipboard manager
    xclip
    
    # Screenshot tool
    flameshot
  ];

  # Link DBeaver configuration if it exists
  xdg.configFile."DBeaverData/workspace6/.metadata/.plugins/org.eclipse.core.runtime/.settings/org.jkiss.dbeaver.core.prefs".source = ./configuration/DBeaver.epf;
}
