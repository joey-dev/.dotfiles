{ config, lib, ... }:

{
  options.roles.vscode.enable = lib.mkEnableOption "the vscode role";

  config = lib.mkIf config.roles.vscode.enable {
    programs.vscode = {
      enable = true;
    };
  };
}
