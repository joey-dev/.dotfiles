# NixOS Development Environment (.dotfiles)
This repository contains a NixOS-based configuration system using home-manager that sets up a complete development environment with i3 window manager, Neovim, and comprehensive development tools.

Always reference these instructions first and fallback to search or bash commands only when you encounter unexpected information that does not match the info here.

## Working Effectively

### Bootstrap and Build the Environment

```bash
# Install home-manager channel (takes ~30 seconds)
make install

# Build the configuration (takes 5-15 minutes depending on cache)
make build

# Apply the configuration
make switch
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
# Check flake configuration (takes less than 10 seconds)
nix flake check

# Verify role structure
for role in alacritty common docker git gtk i3 javascript neovim php sql tmux zsh; do
  if [ ! -f "roles/$role/$role.nix" ]; then
    echo "Error: roles/$role/$role.nix not found"
    exit 1
  fi
  if [ ! -d "roles/$role/configuration" ]; then
    echo "Error: roles/$role/configuration directory not found"
    exit 1
  fi
done

# Build without applying
make build

# Apply configuration
make switch
```

### Known Build Times
- **make install**: 30 seconds
- **make build**: 5-15 minutes (depending on Nix cache availability)
- **make switch**: 5-15 minutes (first run) or 30 seconds (subsequent runs with no changes)
- **nix flake check**: Less than 10 seconds

## Complete End-to-End Validation Scenario

### Fresh System Installation Test
After running `make install` and `make switch`, validate the complete environment:

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

1. Edit individual role `.nix` files in `roles/{role}/{role}.nix`
2. Modify configuration files in `roles/{role}/configuration/`
3. Edit `home.nix` to change which roles are included
4. Update `flake.nix` to change your username or add dependencies

After making changes:
```bash
make build    # Verify the build works
make switch   # Apply the changes
```

### Additional Project Setup
For specific language projects, see [Language-specific Documentation](documentation/PHP.md).

## Common Issues and Troubleshooting

### Known Issues:
1. **Flakes not enabled**: Ensure you have flakes enabled in your Nix configuration:
   ```bash
   mkdir -p ~/.config/nix
   echo "experimental-features = nix-command flakes" >> ~/.config/nix/nix.conf
   ```

2. **Username mismatch**: Update the username in `flake.nix` to match your actual username.

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
home-manager switch --flake .#user --rollback
```

## Frequently Accessed Files and Locations

### Key Configuration Files:
- `flake.nix` - Main Nix flake configuration
- `home.nix` - Home Manager configuration importing all roles
- `Makefile` - Primary commands for installation and building
- `roles/` - Individual NixOS modules for each tool
- `roles/{role}/{role}.nix` - NixOS module for each role
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
- All pull requests automatically run `nix flake check` and role structure validation
- Validates syntax of all `.nix` files