{ config, pkgs, ... }:

{
  # Install CLI tools required by your aliases
  home.packages = with pkgs; [
    thefuck
    nnn
  ];

  programs.zsh = {
    enable = true;
    
    # Native modules for highlighting and suggestions (Better than OMZ plugins on Nix)
    enableCompletion = true;
    autosuggestion.enable = true;
    syntaxHighlighting.enable = true;

    oh-my-zsh = {
      enable = true;
      theme = "nanotech";
      plugins = [
        "sudo"
        "vi-mode"
      ];
    };

    # Read your custom .zshrc file and inject it at the end
    initExtra = builtins.readFile ./configuration/.zshrc;
  };
}