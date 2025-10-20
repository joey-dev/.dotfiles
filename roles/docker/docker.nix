{ config, pkgs, ... }:

{
  # Install Docker
  # Note: Docker typically requires system-level configuration
  # This can be enabled at the system level with:
  # virtualisation.docker.enable = true;
  
  home.packages = with pkgs; [
    docker
    docker-compose
  ];
}
