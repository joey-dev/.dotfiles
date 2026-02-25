{ config, pkgs, ... }:

{
  home.packages = with pkgs; [
    pay-respects
    nnn
  ];

  programs.zsh = {
    enable = true;
    
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

    initExtra = builtins.readFile ./configuration/.zshrc;
  };
}