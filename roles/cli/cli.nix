{
  config,
  lib,
  pkgs,
  ...
}:

{
  options.roles.cli.enable = lib.mkEnableOption "the cli role";

  config = lib.mkIf config.roles.cli.enable {
    home.packages = with pkgs; [
      wget
      curl
      unzip
      htop
      tree
      jq
      fastfetch
      xclip
      yazi
      comma # `, <program>` runs a program without installing it
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

    # Finds which package has a missing command; also builds the database comma uses
    programs.nix-index = {
      enable = true;
      enableZshIntegration = true;
    };
  };
}
