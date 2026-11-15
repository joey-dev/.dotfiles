# The work laptop. Shared settings are in ../common.nix.
{
  pkgs,
  lib,
  nixos-wsl,
  ...
}:

{
  imports = [
    nixos-wsl.nixosModules.default
  ];

  # Bootloader
  boot.loader.systemd-boot.enable = lib.mkForce false;
  boot.loader.efi.canTouchEfiVariables = lib.mkForce false;

  wsl.enable = true;
  wsl.defaultUser = "joey";

  programs.nix-ld.enable = true;
  programs.nix-ld.libraries = with pkgs; [
    # Add any missing dynamic libraries for unpackaged programs
    # here, NOT in environment.systemPackages
  ];

  nixpkgs.hostPlatform = "x86_64-linux";
  networking.networkmanager.enable = lib.mkForce false;

  # This value determines the NixOS release from which the default
  # settings for stateful data, like file locations and database versions
  # on your system were taken. It's perfectly fine and recommended to leave
  # this value at the release version of the first install of this system.
  system.stateVersion = "26.05";
}
