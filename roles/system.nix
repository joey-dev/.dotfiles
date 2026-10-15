# NixOS side of the roles.
# Declares `roles.<name>.enable` for every role folder, so a host can use one role list
# for both Home Manager and NixOS, and imports roles/<name>/system.nix where it exists.
{ lib, ... }:

let
  roleNames = lib.attrNames (lib.filterAttrs (_: type: type == "directory") (builtins.readDir ./.));
  withSystemPart = lib.filter (name: builtins.pathExists ./${name}/system.nix) roleNames;
in
{
  imports = map (name: ./${name}/system.nix) withSystemPart;

  options.roles = lib.genAttrs roleNames (name: {
    enable = lib.mkEnableOption "the ${name} role";
  });
}
