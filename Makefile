# The host to build, a folder in hosts/ (work, personal).
# Defaults to this machine's hostname. Override: make os HOST=work
HOST ?= $(shell hostname)
USERNAME ?= joey

.PHONY: switch os build update check fmt

switch:
	# Apply the Home Manager configuration (shows a diff of what changed)
	nh home switch . --configuration $(USERNAME)@$(HOST)

os:
	# Apply the NixOS configuration (asks for your sudo password)
	nh os switch . --hostname $(HOST)

build:
	# Build the Home Manager configuration without applying it
	nh home build . --configuration $(USERNAME)@$(HOST)

update:
	# Update flake inputs
	nix flake update

check:
	# Build the configuration and run the lint checks
	nix flake check

fmt:
	# Format all .nix files
	nix fmt
