# Home Manager side of every role: imports roles/<name>/<name>.nix for each folder.
# Each role declares its own `roles.<name>.enable` option.
{ lib, ... }:

let
  roleNames = lib.attrNames (lib.filterAttrs (_: type: type == "directory") (builtins.readDir ./.));
in
{
  imports = map (name: ./${name}/${name}.nix) roleNames;
}
