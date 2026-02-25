# PHP project dev shell
# Copy this file to your project root as `shell.nix` and run `nix develop`.
# Or reference it directly: `nix develop path/to/.dotfiles#php`
{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {
  buildInputs = with pkgs; [
    php83
    php83Packages.composer
    phpactor
    phpstan
    php83Packages.phpmd
  ];

  shellHook = ''
    echo "PHP $(php --version | head -1)"
    echo "Composer $(composer --version)"
  '';
}
