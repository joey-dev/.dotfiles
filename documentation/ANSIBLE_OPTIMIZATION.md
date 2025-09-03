# Ansible Optimization for Update Efficiency

## Overview
This optimization implements comprehensive version checking across all Ansible roles to ensure that expensive operations (building from source, downloading packages, installing tools) are only performed when software needs to be installed or updated to newer versions. The goal is to make subsequent runs of the playbook significantly faster while ensuring updates occur when needed.

## Enhanced Version Checking Strategy

### Version Variables (`group_vars/all/vars.yml`)
All software versions are now defined as variables for consistent update checking:
```yaml
# Version specifications for update checking
neovim_version: "0.10"
node_version: "22"  # LTS version
docker_version: "27"  # Major version
chrome_min_version: "130"  # Minimum version for updates
dbeaver_min_version: "24"  # Minimum version for updates
php_version: "8.3"  # Already existed
```

## Key Optimizations Implemented

### 1. Neovim Role (`roles/neovim/tasks/main.yml`)
- **Enhanced nvim version checking**: Uses `neovim_version` variable instead of hardcoded "0.10"
- **Check universal-ctags** before building from source  
- **Check luarocks** before building Lua and luarocks
- **Check npm global packages** before installing:
  - Vue Language Server (`@vue/language-server`)
  - TypeScript (`typescript`)
  - Stylelint (`stylelint`)
  - FixJson (`fixjson`)
  - YAML Language Server (`yaml-language-server`)
- **Check vscode-php-debug** repository before cloning

### 2. JavaScript Role (`roles/javascript/tasks/main.yml`)
- **Enhanced Node.js version checking**: Checks actual Node.js version against `node_version` variable
- **Check if nvm is installed** before downloading/installing
- **Skip installation if correct Node.js version is already installed**

### 3. PHP Role (`roles/php/tasks/main.yml`)
- **Enhanced PHP version checking**: Uses `php_version` variable (8.3)
- **Check Composer** before downloading/installing  
- **Check Composer global packages** before installing:
  - phpMD (`phpmd/phpmd`)
  - phpStan (`phpstan/phpstan`)
  - phpStan strict rules (`phpstan/phpstan-strict-rules`)
  - phpStan phpunit (`phpstan/phpstan-phpunit`)
  - Shipmonk rules (`shipmonk/phpstan-rules`)
  - Jangregor prophecy (`jangregor/phpstan-prophecy`)

### 4. Common Role (`roles/common/tasks/main.yml`)
- **Enhanced Google Chrome version checking**: Uses `chrome_min_version` variable
- **Updates Chrome only if below minimum version**
- **System updates always run** (no version checking for apt update/upgrade)

### 5. Docker Role (`roles/docker/tasks/main.yml`)
- **Enhanced Docker version checking**: Uses `docker_version` variable (major version 27)
- **Skip repository setup and installation if current Docker version is acceptable**

### 6. SQL Role (`roles/sql/tasks/main.yml`)
- **Check DBeaver** before downloading .deb file (existence check remains appropriate for latest downloads)

## Enhanced Version Checking Pattern

The improved version checking follows this pattern:
```yaml
- name: Check if [software] is already installed and get version
  command: [software] --version
  register: [software]_version_check
  failed_when: false
  changed_when: false

- name: [Expensive operation]
  [task details]
  when: [software]_version_check.rc != 0 or not ([desired_version] + '.') in [software]_version_check.stdout
```

### Version Comparison Logic:
- **Not installed**: `rc != 0` (command failed)
- **Wrong version**: `not ([desired_version] + '.') in stdout` (version string not found)
- **Correct version**: Skip installation/update

### Examples:
- **Neovim**: `('NVIM v' + neovim_version) not in neovim_version_check.stdout`
- **Node.js**: `not ('v' + node_version) in current_node_version.stdout`  
- **Docker**: `not (docker_version + '.') in docker_version_check.stdout`
- **Chrome**: `not (chrome_min_version + '.') in chrome_version_check.stdout`

## Benefits

1. **Intelligent updates**: Install only when software is missing or outdated
2. **Faster subsequent runs**: Skip operations when correct versions are installed  
3. **Version consistency**: Use centralized version variables
4. **Update capability**: Upgrade when new versions are specified in variables
5. **Resource efficiency**: Less network bandwidth and CPU time
6. **Better user experience**: Faster local development environment updates

## Testing

Test the optimization locally:
```bash
# First run (will install everything)
make provision

# Update a version variable in group_vars/all/vars.yml
# Second run (will update only changed software)
make provision

# Third run (should be very fast with no changes)
make provision
```

## Update Workflow

To update software versions:
1. Edit `group_vars/all/vars.yml`
2. Update desired version variables
3. Run `make provision` 
4. Only software with version mismatches will be updated

This addresses the feedback: "make ansible not re-install software that is already on the desired version" while maintaining update capability when versions change.