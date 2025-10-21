{ config, pkgs, ... }:

{
  # Install Node.js and JavaScript development tools
  home.packages = with pkgs; [
    nodejs  # This includes npm by default
    nodePackages.pnpm
    nodePackages.yarn
    nodePackages.typescript
    nodePackages.typescript-language-server
    nodePackages.eslint
  ];

  # Prettier as a separate install to avoid LICENSE conflicts
  home.file.".local/bin/prettier".source = "${pkgs.nodePackages.prettier}/bin/prettier";

  # Node.js configuration
  home.sessionVariables = {
    NPM_CONFIG_PREFIX = "$HOME/.npm-global";
  };

  home.sessionPath = [
    "$HOME/.npm-global/bin"
  ];
}
