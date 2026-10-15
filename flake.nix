{
  description = "NixOS dotfiles configuration";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";
    home-manager = {
      url = "github:nix-community/home-manager";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs =
    {
      self,
      nixpkgs,
      home-manager,
      ...
    }:
    let
      system = "x86_64-linux";
      pkgs = import nixpkgs {
        inherit system;
        config.allowUnfree = true;
      };

      # Function to create home configuration for a user
      mkHomeConfiguration =
        username:
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

      # Shell scripts still waiting to be replaced (see PLAN.md, phase 3)
      shellcheckExcludes = [
        "roles/i3/configuration/scripts/Startup/main.sh"
        "roles/i3/configuration/scripts/Windows/window"
      ];

      mkLintCheck =
        name: packages: script:
        pkgs.runCommand "lint-${name}" { nativeBuildInputs = packages; } ''
          cd ${self}
          ${script}
          touch $out
        '';
    in
    {
      homeConfigurations = {
        joey = mkHomeConfiguration "joey";
      };

      # `nix fmt` formats every .nix file in the repo
      formatter.${system} = pkgs.nixfmt-tree;

      # Checks that run when you do `nix flake check`
      checks.${system} = {
        home-manager = self.homeConfigurations.joey.activationPackage;

        nixfmt = mkLintCheck "nixfmt" [ pkgs.nixfmt ] ''
          find . -name '*.nix' -print0 | xargs -0 nixfmt --check
        '';

        statix = mkLintCheck "statix" [ pkgs.statix ] ''
          statix check .
        '';

        deadnix = mkLintCheck "deadnix" [ pkgs.deadnix ] ''
          deadnix --fail .
        '';

        shellcheck = mkLintCheck "shellcheck" [ pkgs.shellcheck ] ''
          scripts=()
          while read -r file; do
            case " ${toString shellcheckExcludes} " in
              *" $file "*) continue ;;
            esac
            if head -n1 "$file" | grep -qE '^#!.*\b(ba)?sh\b'; then
              scripts+=("$file")
            fi
          done < <(find roles -type f -path '*/configuration/*' | sort)
          printf 'shellcheck %s\n' "''${scripts[@]}"
          shellcheck "''${scripts[@]}"
        '';
      };
    };
}
