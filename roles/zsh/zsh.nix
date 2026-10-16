{
  config,
  lib,
  pkgs,
  ...
}:

{
  options.roles.zsh.enable = lib.mkEnableOption "the zsh role";

  config = lib.mkIf config.roles.zsh.enable {
    home.packages = with pkgs; [
      pay-respects
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

      initContent = builtins.readFile ./configuration/.zshrc;
    };

    programs.direnv = {
      enable = true;
      enableZshIntegration = true;
      nix-direnv.enable = true;
    };
  };
}
