install:
	# Install NixOS and home-manager if not already installed
	# This assumes NixOS is already installed
	nix-channel --add https://github.com/nix-community/home-manager/archive/master.tar.gz home-manager
	nix-channel --update

build:
	# Build the home-manager configuration
	home-manager build --flake .#user

switch:
	# Apply the home-manager configuration
	home-manager switch --flake .#user

update:
	# Update flake inputs
	nix flake update

check:
	# Check the flake configuration
	nix flake check
