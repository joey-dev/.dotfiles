# Use it with: nix flake init -t ~/.dotfiles#latest
{
  description = "Latest Development Environment";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
    nix-phps.url = "github:fossar/nix-phps";
  };

  outputs =
    {
      self,
      nixpkgs,
      flake-utils,
      nix-phps,
    }:
    flake-utils.lib.eachDefaultSystem (
      system:
      let
        pkgs = import nixpkgs {
          inherit system;
          config.allowUnfree = true;
        };

        myAtlas = pkgs.stdenv.mkDerivation rec {
          pname = "atlas-cli";
          version = "1.3.3";

          # Map Nix system architecture to Ariga's platform naming
          atlas_platform = "linux-amd64";

          src = pkgs.fetchurl {
            url = "https://release.ariga.io/atlas/atlas-${atlas_platform}-v${version}";

            # Run this once, let it fail, and replace this dummy hash with the correct one from the error!
            hash = "sha256-pB6ma1qq0eNj/YKWE6ZyXDk0N4eS0L5VkSacBBwRK5Y=";
          };

          dontUnpack = true;

          installPhase = ''
            mkdir -p $out/bin
            cp $src $out/bin/atlas
            chmod +x $out/bin/atlas
          '';
        };

        # 1. Force the exact Node.js version
        myNode = pkgs.nodejs_24.overrideAttrs (old: rec {
          version = "24.21.0";
          src = pkgs.fetchurl {
            url = "https://nodejs.org/dist/v${version}/node-v${version}.tar.xz";
            hash = "sha256-pvVN77b9fIT0HboT1h546bTglhcSz2HylxXAX1ztlPw=";
          };
        });

        # 2. Build pnpm natively using npm
        myPnpm = pkgs.stdenv.mkDerivation rec {
          pname = "pnpm";
          version = "12.6.0";

          # Match your computer to the correct GitHub release name
          pnpmTarget = "linux-x64";

          src = pkgs.fetchurl {
            url = "https://github.com/pnpm/pnpm/releases/download/v${version}/pnpm-${pnpmTarget}.tar.gz";
            hash = "sha256-P0xm9mjQ6EIZZ5mC0JWzDaaDJeH6yShOf13BWEvT0T4="; # ⚠️ PASTE YOUR NEW HASH HERE! ⚠️
          };

          # Tell Nix to work inside the extracted folder
          sourceRoot = ".";

          installPhase = ''
            mkdir -p $out/bin

            # Find the binary inside the tar.gz and copy it
            find . -type f -name "pnpm" -exec cp {} $out/bin/pnpm \;

            # Make sure the file is allowed to run
            chmod +x $out/bin/pnpm

            # Create a shortcut for pnpx
            ln -s $out/bin/pnpm $out/bin/pnpx
          '';
        };

        php82 = nix-phps.packages.${system}.php82;

        myPhp = php82.buildEnv {
          extensions = (
            { enabled, all }:
            enabled
            ++ (with all; [
              redis
              amqp
              mysqli
              curl
              mbstring
              intl
              gd
              pdo
              zip
            ])
          );
        };

        ansibleEnv = pkgs.python3.withPackages (
          ps: with ps; [
            ansible-core
            requests
            docker
          ]
        );
      in
      {
        devShells.default = pkgs.mkShell {
          nativeBuildInputs = with pkgs; [
            myPhp
            myPhp.packages.composer

            # 3. Use the new custom versions
            myAtlas
            myNode
            myPnpm

            pre-commit
            gitleaks
            yarn
            mysql84
            git
            ansibleEnv
            lz4
          ];

          shellHook = ''
            export ANSIBLE_PYTHON_INTERPRETER="${ansibleEnv}/bin/python3"

            export DOCKER_CONFIG="$HOME/.docker"
            mkdir -p "$DOCKER_CONFIG"

            alias ansible-playbook="ansible-playbook -e ansible_python_interpreter=$ANSIBLE_PYTHON_INTERPRETER"

            echo "🔨 Environment Loaded"
          '';
        };
      }
    );
}
