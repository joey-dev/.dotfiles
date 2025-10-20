{ config, pkgs, ... }:

{
  # Install Neovim and related tools
  home.packages = with pkgs; [
    neovim
    
    # Language servers and tools
    ripgrep
    fd
    lazygit
    
    # Build tools for Neovim plugins
    gcc
    gnumake
    cmake
    unzip
    tree-sitter
  ];

  # Link Neovim configuration
  xdg.configFile."nvim".source = ./configuration/nvim;
  
  # Link PHP development tools configuration
  home.file.".config/phpmd_ruleset.xml".source = ./configuration/phpmd_ruleset.xml;
  home.file.".config/phpstan_configuration.neon".source = ./configuration/phpstan_configuration.neon;
  home.file.".config/phpstan_stubs".source = ./configuration/phpstan_stubs;
  home.file.".config/plugin_config".source = ./configuration/plugin_config;
}
