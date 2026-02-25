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
      mkHomeConfiguration = username:
        home-manager.lib.homeManagerConfiguration {
          inherit pkgs;
          modules = [
            ./home.nix
            {
              home.username = username;
              home.homeDirectory = "/home/${username}";
            }
          ];
        };
    in
    {
      homeConfigurations = {
        # Default configuration used by CI / nix flake check
        user = mkHomeConfiguration "user";

        # Personal configuration — replace "joey" with your actual system username
        joey = mkHomeConfiguration "joey";
      };

      # Checks that run when you do `nix flake check`
      checks.${system} = {
        home-manager = self.homeConfigurations.user.activationPackage;
      };

      # Development shells — use with `nix develop .#php` or `nix develop .#node`
      # For per-project shells, copy the relevant file from shells/ into your project root.
      devShells.${system} = {
        # PHP development shell: `nix develop .#php`
        php = pkgs.mkShell {
          buildInputs = with pkgs; [
            php83
            php83Packages.composer
            phpactor
            phpstan
            php83Packages.phpmd
          ];
        };

        # Node.js development shell: `nix develop .#node`
        node = pkgs.mkShell {
          buildInputs = with pkgs; [
            nodejs
            nodePackages.pnpm
            nodePackages.yarn
            nodePackages.typescript
            nodePackages.typescript-language-server
          ];
        };

        # Default shell with common tools: `nix develop`
        default = pkgs.mkShell {
          buildInputs = with pkgs; [
            git
            curl
            jq
          ];
        };
      };
    };
}

