{
  config,
  lib,
  pkgs,
  ...
}:

{
  options.roles.neovim.enable = lib.mkEnableOption "the neovim role";

  config = lib.mkIf config.roles.neovim.enable {
    programs.neovim = {
      enable = true;
      withRuby = true;
      withPython3 = true;
    };

    home.packages = with pkgs; [
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
      marksman
      nil
      statix
      sqlfluff
    ];

    # Link Neovim configuration
    xdg.configFile."nvim".source = ./configuration/nvim;
  };
}
