# Intelligent Version Management

The dotfiles repository includes an intelligent version management system that optimizes installation time while providing flexible update control.

## How It Works

The system uses a three-tier approach to version management:

1. **Specific Versions**: Set exact versions for stable, predictable installations
2. **Latest on Missing**: Set `"latest"` to fetch current stable versions only when software is missing
3. **Auto-Update Mode**: Enable `auto_update_*: true` to always fetch and update to latest available versions

The `version_manager` role intelligently determines when to fetch versions:
- Only fetches from APIs when software is missing or auto-update is enabled
- Preserves optimization benefits by skipping unnecessary API calls
- Uses fallback versions when APIs are unavailable

## Configuration

Edit `group_vars/all/vars.yml`:

```yaml
# Base version configuration  
neovim_version: "0.10"          # Specific version - stable installations
node_version: "22"              # LTS major version
docker_version: "27"            # Major version  
chrome_min_version: "130"       # Minimum version threshold

# Auto-update controls - set to true for automatic latest version fetching
auto_update_neovim: false       # Set true to always update to latest
auto_update_node: false         # Set true to always update to latest LTS
auto_update_docker: false       # Set true to always update to latest
auto_update_chrome: false       # Set true to always update to latest
```

## Usage Modes

### Development Environment (Optimized)
- Use specific versions with `auto_update_*: false`
- **First run**: Installs specified versions (~25-50 minutes)
- **Subsequent runs**: Skips when versions match (~2-5 minutes)
- **80-90% time reduction** for repeated runs

### Auto-Updating Environment  
- Set `auto_update_*: true` for software you want to keep current
- Checks for updates on every run
- Automatically installs newer versions when available

### New Environment Setup
- Set versions to `"latest"` for initial setup
- Fetches current stable versions for missing software
- Switches to optimized mode after installation

## Benefits

- **Maximum optimization**: 80-90% time reduction when software is current
- **Flexible updates**: Control exactly which software auto-updates
- **API resilience**: Graceful fallbacks when APIs are blocked
- **Zero maintenance**: No manual version updates needed for auto-update mode
- **Predictable CI**: Reliable operation in restricted environments

## API Sources

- **Neovim**: `https://api.github.com/repos/neovim/neovim/releases/latest`
- **Node.js**: `https://nodejs.org/dist/index.json` (LTS versions)
- **Docker**: `https://api.github.com/repos/docker/cli/releases/latest`
- **Chrome**: `https://versionhistory.googleapis.com/v1/chrome/platforms/linux/channels/stable/versions`

## Example Scenarios

```bash
# Scenario 1: Fast development environment (default)
# - Specific versions, no auto-updates
# - Maximum optimization for repeated runs
make provision  # First run: 25-50 minutes
make provision  # Subsequent: 2-5 minutes

# Scenario 2: Enable auto-updates for Node.js only
# Edit vars.yml: auto_update_node: true
make provision  # Checks for Node.js updates, optimizes others

# Scenario 3: Fresh environment setup
# Edit vars.yml: set versions to "latest" 
make provision  # Fetches current stable versions for missing software
```

The system intelligently balances optimization with update capability, ensuring you get the performance benefits while maintaining control over when software updates occur.