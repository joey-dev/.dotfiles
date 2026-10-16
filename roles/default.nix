# Home Manager side of every role: imports roles/<name>/<name>.nix for each folder.
# Each role declares its own `roles.<name>.enable` option.
{ config, lib, ... }:

let
  roleNames = lib.attrNames (lib.filterAttrs (_: type: type == "directory") (builtins.readDir ./.));
in
{
  imports = map (name: ./${name}/${name}.nix) roleNames;

  options.dotfiles.path = lib.mkOption {
    type = lib.types.str;
    default = "${config.home.homeDirectory}/.dotfiles";
    description = ''
      Where this repo is cloned. Configs linked with `mkOutOfStoreSymlink` point here,
      so edits to them work without a switch.
    '';
  };
}
