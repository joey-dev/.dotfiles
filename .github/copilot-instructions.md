# Ubuntu 20.04 Development Environment (.dotfiles)
This repository contains an Ansible-based configuration system that sets up a complete Ubuntu 20.04 development environment with i3 window manager, Neovim, and comprehensive development tools.

Always reference these instructions first and fallback to search or bash commands only when you encounter unexpected information that does not match the info here.

## Working Effectively

### Bootstrap and Build the Environment
**CRITICAL: NEVER CANCEL long-running commands. Use timeouts of 60+ minutes for builds.**

```bash
# Install Ansible (takes ~30 seconds)
make install

# Full system provision (takes 25-50 minutes total, NEVER CANCEL)
# You will be prompted for sudo password
make provision
```

**WARNING**: The provision step requires sudo password input and takes significant time. Set timeout to 60+ minutes minimum.

### Key Components Installed
- **i3 Window Manager**: Tiling window manager with custom scripts and keybinds
- **Neovim**: Built from source with LazyVim configuration (~2-3 minutes build time)
- **Development Tools**: PHP 8.3, Node.js/npm, Docker, Git, zsh with Oh My Zsh
- **System Tools**: Taskwarrior, fzf, ripgrep, flameshot, rofi, bat
- **Applications**: Google Chrome, Alacritty terminal

### Required System
- **Ubuntu 20.04 only** - This configuration is specifically designed for Ubuntu 20.04
- **Architecture**: amd64/x86_64 required
- **Sudo access**: Required for system package installation
- **Internet connection**: Required for downloading packages and repositories

## Build and Test Commands

### Validation (Run these before and after changes)
```bash
# Validate playbook structure (takes less than 1 second)
./checkPlaybook.sh

# Create hosts file if missing
echo "localhost ansible_connection=local" > hosts

# Dry-run playbook to see what would change (takes 2-5 minutes)
ansible-playbook -i ./hosts playbook.yml -e ansible_python_interpreter=/usr/bin/python3 --check --diff

# List all tasks in playbook (takes less than 1 second)  
ansible-playbook -i ./hosts playbook.yml -e ansible_python_interpreter=/usr/bin/python3 --list-tasks
```

### Known Build Times and Timeouts
- **make install**: 30 seconds (use 2-minute timeout)
- **make provision**: 25-50 minutes (use 60+ minute timeout, NEVER CANCEL)
- **Neovim build**: 1.5-3 minutes (part of provision)
- **System update**: Variable 2-10 minutes (part of provision)  
- **Individual role validation**: 1-5 minutes each

### Testing Infrastructure
```bash
# Vagrant testing setup (may require fixing architecture issues)
make install-test    # Install Vagrant - KNOWN ISSUE: i686 vs amd64 architecture mismatch
make test           # Start Vagrant VM
make test-reload    # Reload Vagrant VM  
make test-new       # Destroy and recreate Vagrant VM
```

**Note**: Current Vagrant configuration downloads i686 instead of amd64 - this is a known issue in the repository.

## Complete End-to-End Validation Scenario

### Fresh System Installation Test
After running `make install` and `make provision`, validate the complete environment:

```bash
# 1. Verify shell environment
echo $SHELL  # Should be /usr/bin/zsh or /bin/zsh
which zsh    # Should show zsh path

# 2. Test development tools
php --version && composer --version
node --version && npm --version  
docker --version && docker compose version
task --version  # Taskwarrior

# 3. Test CLI utilities
fzf --version
rg --version     # ripgrep  
batcat --help    # bat command (aliased as bat in zsh)
git --version

# 4. Launch and test Neovim
nvim --version   # Should show 0.10+ 
# Test actual launch: nvim (should load LazyVim without errors)

# 5. Verify configurations are linked
ls -la ~/.config/nvim     # Should be symlinked to repo
ls -la ~/.config/i3       # Should be symlinked to repo  
ls -la ~/.zshrc          # Should be symlinked to repo
ls -la ~/.taskrc         # Should be symlinked to repo

# 6. Test that basic functionality works
task add "Test task"     # Should create a task
task list               # Should show the test task
task 1 done             # Should complete the task
```

### Expected Installation Time Breakdown
- **System update**: 2-10 minutes (varies by packages needing updates)
- **Common tools**: 2-5 minutes
- **i3 installation**: 1-2 minutes  
- **Alacritty terminal**: 1 minute
- **Zsh + Oh My Zsh**: 2-3 minutes
- **JavaScript/Node.js**: 3-5 minutes
- **Tmux**: 1 minute
- **Neovim build**: 2-3 minutes
- **Git configuration**: less than 1 minute
- **GTK themes**: 1-2 minutes
- **Taskwarrior build**: 2-3 minutes
- **PHP installation**: 3-5 minutes  
- **SQL tools**: 1-2 minutes
- **Docker setup**: 3-5 minutes

**Total estimated time: 25-50 minutes** (NEVER CANCEL, set 60+ minute timeout)

### After Installation, Validate These Scenarios:
1. **Shell Environment**:
   ```bash
   # Test zsh with Oh My Zsh loaded
   echo $SHELL  # Should show /usr/bin/zsh or /bin/zsh
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

5. **i3 Window Manager** (if running on Ubuntu desktop):
   - Logout and login selecting i3 as window manager
   - Test basic shortcuts: Win+d (application launcher), Win+Enter (terminal)

## Configuration and Customization

### Manual Configuration Steps
```bash
# Run interactive configuration for services requiring manual setup
make configure
# This covers: SSH keys, GitHub keys, ProtonPass, DBeaver, WireGuard, Meld
```

### Additional Project Setup
For specific language projects, see [Language-specific Documentation](documentation/PHP.md).

## Common Issues and Troubleshooting

### Known Issues:
1. **python3.8-venv package not found**: The playbook references Python 3.8 specifically for virtual environment support. On some Ubuntu 20.04 installations, the python3.8-venv package may not be available in the default repositories. This will cause a failure but is non-critical to the overall setup.

2. **Vagrant architecture mismatch**: The Makefile downloads i686 Vagrant package instead of amd64. Testing with Vagrant requires manual fix:
   ```bash
   # Fix Vagrant download URL to use amd64
   curl -O https://releases.hashicorp.com/vagrant/2.4.0/vagrant_2.4.0-1_amd64.deb
   sudo apt install ./vagrant_2.4.0-1_amd64.deb
   ```

3. **Interactive configure script**: The configure.sh script requires user input for: SSH keys, GitHub keys, ProtonPass, DBeaver, WireGuard, Meld configuration.

4. **Missing hosts file**: If `hosts` file is missing, create it with: `echo "localhost ansible_connection=local" > hosts`

5. **Build dependencies**: Ensure `build-essential` and development packages are available.

### Recovery Commands:
```bash
# Retry provision if it fails partway through
make provision

# Update Ansible if needed
make update

# Reset specific configurations
ansible-playbook -i ./hosts playbook.yml -e ansible_python_interpreter=/usr/bin/python3 --connection=local --tags={role_name}
```

## Frequently Accessed Files and Locations

### Key Configuration Files:
- `playbook.yml` - Main Ansible playbook defining roles
- `Makefile` - Primary commands for installation and testing
- `roles/` - Individual configuration modules for each tool
- `group_vars/all/vars.yml` - Global variables and versions
- `roles/neovim/files/nvim/` - Neovim LazyVim configuration
- `roles/i3/files/scripts/` - Custom i3 window manager scripts
- `documentation/PHP.md` - PHP-specific project setup instructions

### User Configurations After Install:
- `~/.config/nvim/` - Neovim configuration (symlinked)
- `~/.config/i3/` - i3 window manager configuration (symlinked)  
- `~/.zshrc` - Zsh configuration (symlinked)
- `~/.taskrc` - Taskwarrior configuration (symlinked)

## Important Reminders

- **NEVER CANCEL**: Always wait for builds and provision to complete, even if they take 50+ minutes
- **Ubuntu 20.04 only**: Do not attempt to run on other Ubuntu versions or distributions
- **Sudo required**: The provision step requires administrative privileges
- **Backup first**: This modifies system configurations extensively
- **Internet required**: Many steps download packages and repositories from the internet
- **Test in VM first**: Use Vagrant testing for validating changes before applying to main system

## CI/CD Integration
- GitHub Actions workflow in `.github/workflows/main.yml` validates playbook structure
- All pull requests automatically run `./checkPlaybook.sh` and basic Ansible playbook validation
- Always run `./checkPlaybook.sh` before committing changes