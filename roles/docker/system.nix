{
  config,
  lib,
  username,
  ...
}:

{
  config = lib.mkIf config.roles.docker.enable {
    virtualisation.docker.enable = true;

    users.users.${username}.extraGroups = [ "docker" ];
  };
}
