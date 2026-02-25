{ config, pkgs, ... }:

{
  # Install SQL and database tools
  home.packages = with pkgs; [
    # Database clients
    postgresql
    mysql80
    sqlite
    
    # Database GUI tools
    dbeaver-bin
    
    # Command-line database tools
    pgcli
    # mycli is currently broken in nixpkgs (sqlglot version conflict); use: nix run nixpkgs#mycli
    litecli
  ];
}
