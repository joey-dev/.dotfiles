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
    mycli
    litecli
  ];
}
