# Node.js project dev shell
# Copy this file to your project root as `shell.nix` and run `nix develop`.
# Or reference it directly: `nix develop path/to/.dotfiles#node`
{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {
  buildInputs = with pkgs; [
    nodejs
    nodePackages.pnpm
    nodePackages.yarn
    nodePackages.typescript
    nodePackages.typescript-language-server
  ];

  shellHook = ''
    echo "Node $(node --version)"
    echo "npm $(npm --version)"
  '';
}
