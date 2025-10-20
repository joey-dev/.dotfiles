{ config, pkgs, ... }:

{
  # Install Node.js and JavaScript development tools
  home.packages = with pkgs; [
    nodejs
    nodePackages.npm
    nodePackages.pnpm
    nodePackages.yarn
    nodePackages.typescript
    nodePackages.typescript-language-server
    nodePackages.eslint
    nodePackages.prettier
  ];

  # Node.js configuration
  home.sessionVariables = {
    NPM_CONFIG_PREFIX = "$HOME/.npm-global";
  };

  home.sessionPath = [
    "$HOME/.npm-global/bin"
  ];
}
