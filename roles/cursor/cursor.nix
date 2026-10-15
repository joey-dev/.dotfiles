{
  config,
  lib,
  pkgs,
  ...
}:

{
  options.roles.cursor.enable = lib.mkEnableOption "the cursor role";

  config = lib.mkIf config.roles.cursor.enable {
    home.packages = with pkgs; [
      code-cursor
    ];
  };
}
