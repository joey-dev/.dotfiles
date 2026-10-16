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
      # Pass the generated provider settings as wrapper arguments instead of writing
      # nvim/init.lua, which would land inside the linked config folder
      sideloadInitLua = true;
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

    # Linked to the repo, not the store: edits work right away, and lazy.nvim
    # writes lazy-lock.json and lazyvim.json straight into the repo
    xdg.configFile."nvim".source =
      config.lib.file.mkOutOfStoreSymlink "${config.dotfiles.path}/roles/neovim/configuration/nvim";
  };
}
