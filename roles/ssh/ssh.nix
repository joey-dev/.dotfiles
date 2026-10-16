{ config, lib, ... }:

{
  options.roles.ssh.enable = lib.mkEnableOption "the ssh role";

  config = lib.mkIf config.roles.ssh.enable {
    services.ssh-agent.enable = true;

    programs.ssh = {
      enable = true;
      enableDefaultConfig = false;
      # Hosts and keys that are not in git
      includes = [ "config.local" ];
      # Ask for the passphrase on first use, then keep the key in the agent
      settings."*".AddKeysToAgent = "yes";
    };
  };
}
