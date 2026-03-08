{ config, pkgs, lib, ... }:

{
  # Import all role modules
  imports = [
    ./roles/alacritty/alacritty.nix
    ./roles/common/common.nix
    ./roles/docker/docker.nix
    ./roles/ghostty/ghostty.nix
    ./roles/git/git.nix
    ./roles/gtk/gtk.nix
    ./roles/i3/i3.nix
    ./roles/javascript/javascript.nix
    ./roles/neovim/neovim.nix
    ./roles/php/php.nix
    ./roles/polybar/polybar.nix
    ./roles/sql/sql.nix
    ./roles/tmux/tmux.nix
    ./roles/zsh/zsh.nix
  ];

  # Home Manager needs a bit of information about you and the
  # paths it should manage.
  # These are now provided by flake.nix
  # home.username and home.homeDirectory are set in the flake

  # This value determines the Home Manager release that your
  # configuration is compatible with. This helps avoid breakage
  # when a new Home Manager release introduces backwards
  # incompatible changes.
  #
  # You can update Home Manager without changing this value. See
  # the Home Manager release notes for a list of state version
  # changes in each release.
  home.stateVersion = "24.05";

  # Let Home Manager install and manage itself.
  programs.home-manager.enable = true;
}
