{ config, pkgs, ... }:

{
  # Install Docker CLI tools
  # Note: For Docker daemon on NixOS, add this to your system configuration:
  #   virtualisation.docker.enable = true;
  # For non-NixOS systems, Docker needs to be installed separately
  
  home.packages = with pkgs; [
    docker
    docker-compose
  ];
}
