{
  config,
  lib,
  pkgs,
  ...
}:

{
  options.roles.javascript.enable = lib.mkEnableOption "the javascript role";

  config = lib.mkIf config.roles.javascript.enable {
    # Install Node.js and JavaScript development tools
    home.packages = with pkgs; [
      nodejs # This includes npm by default
      pnpm
      yarn
      typescript
      typescript-language-server
      eslint
      # prettier removed - install per-project or use: nix run nixpkgs#prettier
    ];
  };
}
