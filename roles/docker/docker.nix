{ config, lib, ... }:

{
  options.roles.docker.enable = lib.mkEnableOption "the docker role";

  config = lib.mkIf config.roles.docker.enable {
    # Docker itself is enabled in ./system.nix (NixOS side)
  };
}
