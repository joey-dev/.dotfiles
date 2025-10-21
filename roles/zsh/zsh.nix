{ config, pkgs, ... }:

{
  # Install zsh and related tools
  home.packages = with pkgs; [
    zsh
    zsh-autosuggestions
    zsh-syntax-highlighting
    oh-my-zsh
  ];

  # Zsh configuration using home-manager
  programs.zsh = {
    enable = true;
    enableCompletion = true;
    autosuggestion.enable = true;
    syntaxHighlighting.enable = true;
    
    oh-my-zsh = {
      enable = true;
      theme = "robbyrussell";
      plugins = [ "git" "docker" "npm" "node" ];
    };
  };

  # Link zsh configuration
  home.file.".zshrc".source = ./configuration/.zshrc;
}
