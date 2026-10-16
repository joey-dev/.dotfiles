{
  config,
  lib,
  pkgs,
  ...
}:

{
  options.roles.gui-editors.enable = lib.mkEnableOption "the gui-editors role";

  config = lib.mkIf config.roles.gui-editors.enable {
    home.packages = with pkgs; [
      code-cursor
    ];

    programs.vscode = {
      enable = true;
    };
  };
}
