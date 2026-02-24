# Read the username from local.nix if it exists, otherwise fall back to the
# current system user. This means `make switch` works out of the box after
# copying local.nix.example to local.nix.
USERNAME := $(shell grep -o 'username = "[^"]*"' local.nix 2>/dev/null | sed 's/username = "\(.*\)"/\1/' || whoami)

install:
	# Install NixOS and home-manager if not already installed
	# This assumes NixOS is already installed
	nix-channel --add https://github.com/nix-community/home-manager/archive/master.tar.gz home-manager
	nix-channel --update

build:
	# Build the home-manager configuration
	# --impure is required so Nix can read local.nix (which is gitignored)
	home-manager build --flake .#${USERNAME} --impure

switch:
	# Apply the home-manager configuration
	# --impure is required so Nix can read local.nix (which is gitignored)
	home-manager switch --flake .#${USERNAME} --impure

update:
	# Update flake inputs
	nix flake update

check:
	# Check the flake configuration (pure evaluation, does not need local.nix)
	nix flake check

