# NixOS Migration Complete

This document describes the new NixOS-based structure of this dotfiles repository.

## Structure Overview

The repository now uses NixOS with home-manager for declarative system configuration management.

### Main Configuration Files

- **flake.nix**: Main Nix flake configuration that defines inputs (nixpkgs, home-manager) and outputs (home configurations)
- **home.nix**: Home Manager configuration that imports all role modules
- **Makefile**: Commands for building and applying the configuration

### Role Structure

Each role follows this structure:
```
roles/{role}/
├── {role}.nix          # NixOS module defining packages and configuration
└── configuration/      # Configuration files for the role
    └── ...            # Role-specific configuration files
```

### Available Roles

1. **alacritty**: Terminal emulator with configuration
2. **common**: Common utilities (wget, curl, ripgrep, fzf, bat, etc.)
3. **docker**: Docker and docker-compose
4. **git**: Git with Meld as merge tool
5. **gtk**: GTK theme configuration
6. **i3**: i3 window manager with custom scripts
7. **javascript**: Node.js, npm, and JavaScript development tools
8. **neovim**: Neovim with LazyVim configuration
9. **php**: PHP 8.3 with Composer and development tools
10. **sql**: Database tools (PostgreSQL, MySQL, SQLite, DBeaver)
11. **tmux**: Tmux terminal multiplexer
12. **zsh**: Zsh shell with Oh My Zsh

## Installation

1. **Prerequisites**: NixOS with flakes enabled

2. **Enable flakes** (if not already enabled):
   ```bash
   mkdir -p ~/.config/nix
   echo "experimental-features = nix-command flakes" >> ~/.config/nix/nix.conf
   ```

3. **Clone and install**:
   ```bash
   git clone <repository-url> ~/.dotfiles
   cd ~/.dotfiles
   
   # Edit flake.nix and replace 'user' with your actual username in the homeConfigurations section
   # Example: change "user = home-manager.lib..." to "yourname = home-manager.lib..."
   
   make install  # Add home-manager channel
   make switch   # Apply configuration (use 'make switch --flake .#yourname' with your username)
   ```

## Usage

- **Build configuration**: `make build`
- **Apply configuration**: `make switch`
- **Update dependencies**: `make update`
- **Validate configuration**: `make check`

## What Changed from Ansible

### Removed
- All Ansible playbooks and configuration files
- Ubuntu/Debian specific installation logic
- Vagrant testing infrastructure
- Shell scripts for provisioning

### Added
- Nix flake configuration
- Home Manager integration
- Declarative package management
- Reproducible builds
- Faster configuration application

### Benefits
- **Reproducible**: Same configuration produces same results
- **Atomic**: Configuration changes are atomic
- **Rollback**: Easy to roll back to previous configurations
- **Fast**: Nix binary cache makes installation much faster
- **Declarative**: All configuration in version control

## Migration Notes

All configuration files from the old Ansible structure have been preserved in the new `roles/{role}/configuration/` directories. The NixOS modules in `roles/{role}/{role}.nix` now reference these configuration files and install the necessary packages.

The repository structure is cleaner and more maintainable with this new approach.
