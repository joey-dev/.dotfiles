# Automated Version Management

The dotfiles repository now supports automated version fetching for software installations. Instead of manually updating version numbers in `group_vars/all/vars.yml`, you can use "latest" to automatically fetch the most recent stable versions.

## How It Works

The `version_manager` role runs before all other roles and:

1. **Fetches latest versions** from official APIs when "latest" is specified
2. **Falls back to known stable versions** if APIs are unavailable (common in CI environments)
3. **Updates version variables** for use by subsequent roles
4. **Maintains compatibility** with specific version numbers

## Supported Software

- **Neovim**: GitHub releases API (fallback: 0.10)
- **Node.js**: Node.js dist API for LTS versions (fallback: 22)
- **Docker**: GitHub releases API (fallback: 27)
- **Chrome**: Google Version History API (fallback: 130)
- **DBeaver**: Manual specification required

## Configuration

Edit `group_vars/all/vars.yml`:

```yaml
# Use "latest" for automatic fetching, or specify exact versions
neovim_version: "latest"        # Auto-fetch latest stable
node_version: "latest"          # Auto-fetch latest LTS  
docker_version: "latest"        # Auto-fetch latest stable
chrome_min_version: "latest"    # Auto-fetch latest stable
dbeaver_min_version: "24"       # Specific version required
```

## Benefits

- **Automatic updates**: Always get the latest stable versions
- **No manual maintenance**: No need to update version numbers manually
- **Fallback safety**: Works even when APIs are blocked
- **Selective control**: Mix "latest" with specific versions as needed
- **CI-friendly**: Handles network restrictions gracefully

## Example Usage

```bash
# First run with latest versions
make provision

# Software automatically updates to latest stable versions
# Subsequent runs skip installation if versions match

# To force specific versions, edit vars.yml:
# neovim_version: "0.9"  # Force older version
# node_version: "latest" # Keep auto-updating

make provision  # Only updates changed software
```

## API Sources

- **Neovim**: `https://api.github.com/repos/neovim/neovim/releases/latest`
- **Node.js**: `https://nodejs.org/dist/index.json`
- **Docker**: `https://api.github.com/repos/docker/cli/releases/latest`
- **Chrome**: `https://versionhistory.googleapis.com/v1/chrome/platforms/linux/channels/stable/versions/all/releases`

The system gracefully handles API failures and uses fallback versions to ensure installation always succeeds.