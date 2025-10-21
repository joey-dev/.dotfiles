{ config, pkgs, ... }:

{
  # Install zsh and related tools
  home.packages = with pkgs; [
    zsh
    zsh-autosuggestions
    zsh-syntax-highlighting
    oh-my-zsh
  ];

  # Link custom zsh configuration
  # Note: We don't use programs.zsh.enable to avoid conflicts with the custom .zshrc
  home.file.".zshrc".source = ./configuration/.zshrc;
}
