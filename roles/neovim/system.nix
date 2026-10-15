{ config, lib, ... }:

{
  config = lib.mkIf config.roles.neovim.enable {
    # Runs the prebuilt binaries Mason downloads (LSPs, formatters, debug adapters)
    programs.nix-ld.enable = true;
  };
}
