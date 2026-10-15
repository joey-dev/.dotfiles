# personal

The personal laptop's NixOS files are not in the repo yet.

Until then, only its Home Manager config (`joey@personal`) exists.

## Adding them

On the personal laptop:

1. Copy the hardware file:

   ```bash
   cp /etc/nixos/hardware-configuration.nix ~/.dotfiles/hosts/personal/
   ```

2. Create `configuration.nix` here, like `../work/configuration.nix`:
   - Import `./hardware-configuration.nix`.
   - Copy only what is **specific to this laptop** from `/etc/nixos/configuration.nix`. For example the LUKS swap device and `system.stateVersion`.
   - Everything shared is already in `../common.nix`. Compare with it to see what is left.

3. Check and switch:

   ```bash
   nix flake check
   sudo nixos-rebuild switch --flake ~/.dotfiles#personal
   ```

`flake.nix` picks up `nixosConfigurations.personal` by itself once `configuration.nix` exists.
