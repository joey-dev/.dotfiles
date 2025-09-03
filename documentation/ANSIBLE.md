# Ansible Configuration and Optimization Guide

This guide covers the complete Ansible configuration system for the dotfiles repository, including intelligent version management, optimization strategies, and maintenance procedures.

## Smart Version Management System

The dotfiles repository implements an intelligent version management system that automatically fetches the latest software versions and only updates when necessary, achieving both optimization and automatic updates.

### How It Works

The system uses a simple three-step process for each software component:

1. **Check installed version** - Extract current version from software (`nvim --version`, `node --version`, etc.)
2. **Fetch latest version** - Query official APIs for current stable releases
3. **Compare and update** - Use semantic version comparison to determine if update is needed

### Performance Characteristics

- **Up-to-date system**: Skip all installations (~2-5 minutes total)
- **Outdated software**: Update only what needs updating (~5-25 minutes)  
- **New environment**: Install latest versions (~25-50 minutes)
- **Blocked APIs**: Graceful fallback to known stable versions

### Configuration

Edit `group_vars/all/vars.yml` to control software versions:

```yaml
# Software versions - automatically updated to latest stable releases
neovim_version: "latest"      # Fetches from GitHub releases API
node_version: "latest"        # Fetches latest LTS from Node.js API
docker_version: "latest"      # Fetches from Docker GitHub releases
chrome_version: "latest"      # Fetches from Google Chrome API
php_version: "8.3"            # Static version (manual updates)
```

## Optimization Strategy

### Version Checking Pattern

Each role implements intelligent version checking to skip expensive operations:

```yaml
- name: Check if software is installed and get version
  command: software --version
  register: software_version_check
  failed_when: false
  changed_when: false

- name: Get latest version from API
  uri:
    url: https://api.github.com/repos/owner/repo/releases/latest
    method: GET
    return_content: yes
  register: software_latest_response
  failed_when: false

- name: Compare versions and determine if update needed
  set_fact:
    software_needs_update: "{{ latest_version is version(installed_version, '>') }}"

- name: Install/update software
  [expensive operation]
  when: software_needs_update
```

### Benefits

- **Intelligent updates**: Install only when software is missing or outdated
- **Maximum efficiency**: 80-90% time reduction for repeated runs when software is current
- **Zero maintenance**: No manual version file updates required
- **Always current**: Automatically gets latest stable releases
- **API resilient**: Graceful fallbacks when APIs are blocked (common in CI)

## Adding New Software

To add version management for new software:

1. **Add version variable** to `group_vars/all/vars.yml`:
   ```yaml
   new_software_version: "latest"  # Or specific version like "1.2.3"
   ```

2. **Implement version checking** in the role's `tasks/main.yml`:
   ```yaml
   - name: Check installed version
     command: new-software --version
     register: new_software_version_check
     failed_when: false
     changed_when: false

   - name: Extract installed version
     set_fact:
       new_software_installed_version: "{{ version_output | regex_extract_pattern }}"

   - name: Get latest version from API (if using "latest")
     uri:
       url: https://api.provider.com/latest
       method: GET
       return_content: yes
     register: new_software_latest_response
     failed_when: false
     when: new_software_version == "latest"

   - name: Set target version
     set_fact:
       new_software_target_version: "{{ new_software_version if new_software_version != 'latest' else api_response.version }}"

   - name: Compare versions
     set_fact:
       new_software_needs_update: "{{ new_software_target_version is version(new_software_installed_version, '>') }}"

   - name: Install/update software
     [installation tasks]
     when: new_software_needs_update
   ```

3. **Add fallback version** for API failures:
   ```yaml
   - name: Set fallback version if API fails
     set_fact:
       new_software_target_version: "1.2.3"  # Known stable version
     when: new_software_version == "latest" and (api_response is not defined or api_response.status != 200)
   ```

## Role-Specific Implementation

### Neovim (`roles/neovim/tasks/main.yml`)
- Checks for NVIM version using `nvim --version`
- Fetches latest from GitHub releases API
- Includes dependency checks (luarocks, universal-ctags, npm packages)
- Builds from source only when version mismatch detected

### Node.js (`roles/javascript/tasks/main.yml`)
- Checks Node.js version through nvm
- Fetches latest LTS from Node.js distribution API
- Installs/updates nvm and Node.js only when needed

### Docker (`roles/docker/tasks/main.yml`)
- Checks Docker version using `docker --version`
- Fetches latest from Docker CLI GitHub releases
- Skips repository setup when current version is acceptable

### Chrome (`roles/common/tasks/main.yml`)
- Checks Chrome version using `google-chrome --version`
- Fetches latest from Google Chrome version history API
- Downloads and installs .deb package only for version updates

### PHP (`roles/php/tasks/main.yml`)
- Uses static version configuration (8.3)
- Checks Composer and global packages before installation
- Optimizes composer package installations

## API Sources and Fallbacks

- **Neovim**: `https://api.github.com/repos/neovim/neovim/releases/latest` → fallback: "0.10.2"
- **Node.js**: `https://nodejs.org/dist/index.json` (LTS filter) → fallback: "22.12.0"
- **Docker**: `https://api.github.com/repos/docker/cli/releases/latest` → fallback: "27.3.1"
- **Chrome**: `https://versionhistory.googleapis.com/v1/chrome/platforms/linux/channels/stable/versions` → fallback: "131.0.6778.108"

## Testing and Validation

### Quick Validation
```bash
# Validate playbook structure
./checkPlaybook.sh

# Dry-run to see what would change
ansible-playbook -i ./hosts playbook.yml --check --diff

# List all tasks
ansible-playbook -i ./hosts playbook.yml --list-tasks
```

### Performance Testing
```bash
# First run (new environment) - expect 25-50 minutes
time make provision

# Second run (up-to-date) - expect 2-5 minutes  
time make provision

# Update a version in vars.yml and test selective update
time make provision
```

## Troubleshooting

### Common Issues

1. **Empty version variables**: The system includes safety checks to prevent empty version comparisons
2. **API failures**: Graceful fallbacks ensure installation continues with known stable versions
3. **Network restrictions**: CI environments often block external APIs - fallback versions handle this

### Recovery Commands

```bash
# Retry if provision fails partway
make provision

# Target specific role for debugging
ansible-playbook -i ./hosts playbook.yml --tags=neovim

# Force reinstall by setting version to 0.0.0 temporarily
# Edit vars.yml, run provision, then restore correct version
```

## Migration from Static Versions

To migrate existing static version configurations:

1. **Replace static versions** with "latest" in `vars.yml`
2. **Add API fetching logic** to the role's tasks
3. **Test with dry-run** to verify expected behavior
4. **Validate performance** improvement on subsequent runs

This system maintains the 80-90% optimization benefits while providing automatic updates and eliminating manual version maintenance.