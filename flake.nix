{
  description = "NixOS dotfiles configuration";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";
    home-manager = {
      url = "github:nix-community/home-manager";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs = { self, nixpkgs, home-manager, ... }:
    let
      system = "x86_64-linux";
      pkgs = nixpkgs.legacyPackages.${system};

      # Function to create home configuration for a user
      # Optionally pass a list of extra modules (e.g., inline git identity config)
      mkHomeConfiguration = { username, extraModules ? [] }:
        home-manager.lib.homeManagerConfiguration {
          inherit pkgs;

          modules = [
            ./home.nix
            {
              home.username = username;
              home.homeDirectory = "/home/${username}";
            }
          ] ++ extraModules;
        };

      # Load local.nix if it exists (requires --impure flag when running locally).
      # In CI (pure evaluation), local.nix is gitignored so pathExists returns false.
      localConfig = if builtins.pathExists ./local.nix then import ./local.nix else null;
    in
    {
      homeConfigurations =
        # Default 'user' configuration used by CI / nix flake check
        { user = mkHomeConfiguration { username = "user"; }; }
        # Personal configuration loaded from local.nix (if present, requires --impure)
        // (if localConfig != null
            then { ${localConfig.username} = mkHomeConfiguration localConfig; }
            else { });

      # Checks that run when you do `nix flake check` (pure evaluation, no local.nix)
      checks.${system} = {
        home-manager = self.homeConfigurations.user.activationPackage;
      };
    };
}

