# NixOS Development Environment (.dotfiles)
This repository contains a NixOS-based configuration system using home-manager that sets up a complete development environment with i3 window manager, Neovim, and comprehensive development tools.

Always reference these instructions first and fallback to search or bash commands only when you encounter unexpected information that does not match the info here.

## Working Effectively

### Bootstrap and Build the Environment

Each laptop is a host in `hosts/` (`work`, `personal`). Commands pick the host from the hostname; override with `HOST=<host>`.

```bash
# First-time setup of a laptop (NixOS + Home Manager)
./bootstrap.sh <host>

# Build the Home Manager configuration (takes 5-15 minutes depending on cache)
make build

# Apply the Home Manager configuration
make switch

# Apply the NixOS configuration (needs sudo)
make os
```

### Key Components Installed
- **i3 Window Manager**: Tiling window manager with custom scripts and keybinds
- **Neovim**: LazyVim configuration
- **Development Tools**: PHP 8.3, Node.js/npm, Docker, Git, zsh with Oh My Zsh
- **System Tools**: fzf, ripgrep, bat, htop, flameshot, rofi
- **Applications**: Alacritty terminal

### Required System
- **NixOS** - This configuration uses NixOS with flakes
- **Architecture**: x86_64-linux
- **Flakes enabled**: Required for using this configuration
- **Internet connection**: Required for downloading packages from Nix cache

## Build and Test Commands

### Validation (Run these before and after changes)
```bash
# Format all .nix files (nixfmt)
nix fmt

# Build the configuration and run all lint checks:
# nixfmt, statix, deadnix and shellcheck (see `checks` in flake.nix)
nix flake check
```

### Known Build Times
- **make build**: 5-15 minutes (depending on Nix cache availability)
- **make switch**: 5-15 minutes (first run) or 30 seconds (subsequent runs with no changes)
- **nix flake check**: a few minutes (it builds the Home Manager configuration)

## Complete End-to-End Validation Scenario

### Fresh System Installation Test
After running `./bootstrap.sh <host>`, validate the complete environment:

```bash
# 1. Verify shell environment
echo $SHELL  # Should be /bin/zsh or similar
which zsh    # Should show zsh path

# 2. Test development tools
php --version && composer --version
node --version && npm --version  
docker --version && docker compose version

# 3. Test CLI utilities
fzf --version
rg --version     # ripgrep  
bat --version
git --version

# 4. Launch and test Neovim
nvim --version   # Should show Neovim version
# Test actual launch: nvim (should load LazyVim without errors)

# 5. Verify configurations are linked
ls -la ~/.config/nvim     # Should point to nix store
ls -la ~/.config/i3       # Should point to nix store  
ls -la ~/.zshrc          # Should point to nix store

# 6. Test that basic functionality works
# Launch applications to verify they work correctly
```

### Expected Installation Time Breakdown
- **Initial flake evaluation**: 30 seconds
- **Downloading packages**: 3-10 minutes (from Nix cache)
- **Building configuration**: 1-2 minutes
- **Activating home-manager**: 1-2 minutes

**Total estimated time: 5-15 minutes** (much faster with Nix binary cache)

### After Installation, Validate These Scenarios:
1. **Shell Environment**:
   ```bash
   # Test zsh with Oh My Zsh loaded
   echo $SHELL
   # Test auto-suggestions and syntax highlighting work
   ```

2. **Neovim Functionality**:
   ```bash
   # Launch Neovim and verify LazyVim loads
   nvim
   # Should load without errors, LazyVim splash screen appears
   # Test basic editing and plugin functionality
   # Exit with :q
   ```

3. **Development Tools**:
   ```bash
   # Verify PHP installation
   php --version  # Should show PHP 8.3.x
   composer --version  # Should show Composer

   # Verify Node.js installation
   node --version  # Should show latest Node.js version
   npm --version   # Should show npm version

   # Verify Docker installation
   docker --version  # Should show Docker version
   docker compose version  # Should show Docker Compose
   ```

4. **System Tools**:
   ```bash
   # Test Taskwarrior
   task --version  # Should show Taskwarrior 2.6.2

   # Test other CLI tools
   fzf --version
   rg --version    # ripgrep
   batcat --version  # bat (aliased as bat in zsh)
   ```


3. **Development Tools**:
   ```bash
   # Verify PHP installation
   php --version  # Should show PHP 8.3.x
   composer --version  # Should show Composer

   # Verify Node.js installation
   node --version  # Should show latest Node.js version
   npm --version   # Should show npm version

   # Verify Docker installation
   docker --version  # Should show Docker version
   docker compose version  # Should show Docker Compose
   ```

4. **System Tools**:
   ```bash
   # Test CLI tools
   fzf --version
   rg --version    # ripgrep
   bat --version
   ```

5. **i3 Window Manager** (if running on NixOS with display manager):
   - Logout and login selecting i3 as window manager
   - Test basic shortcuts: Win+d (application launcher), Win+Enter (terminal)

## Configuration and Customization

### Customizing Your Setup
To customize the configuration:

1. Edit individual role `.nix` files in `roles/{role}/{role}.nix` (Home Manager part)
2. Edit `roles/{role}/system.nix` for the NixOS part of a role (only docker, i3, neovim, php have one)
3. Modify configuration files in `roles/{role}/configuration/`
4. Edit `hosts/roles.nix` to change which roles are enabled
5. Edit `hosts/common.nix` for shared NixOS settings, `hosts/{host}/configuration.nix` for one laptop
6. Update `flake.nix` to add hosts or inputs

Every role has a `roles.{role}.enable` option and wraps its config in `lib.mkIf`. New role folders are imported automatically by `roles/default.nix` and `roles/system.nix`.

After making changes:
```bash
make build    # Verify the build works
make switch   # Apply Home Manager changes
make os       # Apply NixOS changes
```

### Additional Project Setup
For specific language projects, see [Language-specific Documentation](documentation/PHP.md).

## Common Issues and Troubleshooting

### Known Issues:
1. **Flakes not enabled**: `bootstrap.sh` passes the flag itself. After the first NixOS switch, flakes are enabled by `hosts/common.nix`.

2. **Hostname mismatch**: `make` uses the hostname to pick `hosts/<host>`. Use `make switch HOST=work` if they differ.

3. **Build failures**: If a build fails, check the error message. Common issues:
   - Missing or incorrect package names
   - Syntax errors in `.nix` files
   - Configuration file paths that don't exist

### Recovery Commands:
```bash
# Check configuration validity
nix flake check

# Rebuild configuration
make build

# Update flake inputs
make update

# Roll back to previous generation
home-manager generations  # List available generations
# then run the activate script of the generation you want, e.g.:
# /nix/store/<hash>-home-manager-generation/activate
```

## Frequently Accessed Files and Locations

### Key Configuration Files:
- `flake.nix` - Hosts, Home Manager and NixOS configurations, lint checks
- `hosts/roles.nix` - Roles enabled on every laptop
- `hosts/home.nix` - Home Manager settings shared by every host
- `hosts/common.nix` - NixOS settings shared by every host
- `hosts/{host}/` - `configuration.nix` and `hardware-configuration.nix` per laptop
- `Makefile` - Primary commands for building and switching
- `roles/{role}/{role}.nix` - Home Manager module for each role
- `roles/{role}/system.nix` - Optional NixOS module for a role
- `roles/{role}/configuration/` - Configuration files for each role
- `documentation/PHP.md` - PHP-specific project setup instructions

### User Configurations After Install:
- `~/.config/nvim/` - Neovim configuration (managed by Nix)
- `~/.config/i3/` - i3 window manager configuration (managed by Nix)
- `~/.zshrc` - Zsh configuration (managed by Nix)
- `~/.tmux.conf` - Tmux configuration (managed by Nix)

## Important Reminders

- **NixOS required**: This configuration is designed for NixOS with home-manager
- **Flakes enabled**: Ensure flakes are enabled in your Nix configuration
- **Declarative**: All configuration is declarative and reproducible
- **Internet required**: Initial setup downloads packages from Nix binary cache
- **No sudo needed**: Home Manager doesn't require sudo for user-level configuration

## CI/CD Integration
- GitHub Actions workflow in `.github/workflows/main.yml` validates NixOS configuration
- Pull requests and pushes to `master` run `nix flake check`
- This builds the Home Manager configuration and runs nixfmt, statix, deadnix and shellcheck
- Shell scripts in `roles/*/configuration` must pass shellcheck; `shellcheckExcludes` in `flake.nix` lists temporary exceptions
- statix settings live in `statix.toml`