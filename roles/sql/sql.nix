{
  config,
  lib,
  pkgs,
  ...
}:

{
  options.roles.sql.enable = lib.mkEnableOption "the sql role";

  config = lib.mkIf config.roles.sql.enable {
    # Install SQL and database tools
    home.packages = with pkgs; [
      # Database clients
      postgresql
      mariadb.client
      sqlite

      # Database GUI tools
      dbeaver-bin

      # Command-line database tools
      pgcli
      # mycli is currently broken in nixpkgs (sqlglot version conflict); use: nix run nixpkgs#mycli
      litecli
    ];
  };
}
