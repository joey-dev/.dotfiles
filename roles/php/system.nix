{ config, lib, ... }:

{
  config = lib.mkIf config.roles.php.enable {
    # Xdebug in Docker connects back to the editor on this port
    networking.firewall.allowedTCPPorts = [ 9003 ];
  };
}
