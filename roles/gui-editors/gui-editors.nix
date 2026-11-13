{
  config,
  lib,
  pkgs,
  ...
}:

{
  options.roles.gui-editors.enable = lib.mkEnableOption "the gui-editors role";

  config = lib.mkIf config.roles.gui-editors.enable {
    programs.vscode = {
      enable = true;
    };
  };
}
