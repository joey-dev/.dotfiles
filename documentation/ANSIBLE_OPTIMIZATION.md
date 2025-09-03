# Ansible Optimization for Update Efficiency

## Overview
This optimization implements version checking across all Ansible roles to ensure that expensive operations (building from source, downloading packages, installing tools) are only performed when necessary. The goal is to make subsequent runs of the playbook significantly faster while ensuring system updates always occur.

## Key Optimizations Implemented

### 1. Neovim Role (`roles/neovim/tasks/main.yml`)
- **Check nvim version** before building from source (saves ~2-3 minutes)
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
- **Check if nvm is installed** before downloading/installing
- **Check if node is installed** before installing via nvm

### 3. PHP Role (`roles/php/tasks/main.yml`)
- **Check PHP version** before adding repositories and installing packages
- **Check Composer** before downloading/installing  
- **Check Composer global packages** before installing:
  - phpMD (`phpmd/phpmd`)
  - phpStan (`phpstan/phpstan`)
  - phpStan strict rules (`phpstan/phpstan-strict-rules`)
  - phpStan phpunit (`phpstan/phpstan-phpunit`)
  - Shipmonk rules (`shipmonk/phpstan-rules`)
  - Jangregor prophecy (`jangregor/phpstan-prophecy`)

### 4. Common Role (`roles/common/tasks/main.yml`)
- **Check Google Chrome** before downloading .deb file
- **System updates always run** (no version checking for apt update/upgrade)

### 5. Docker Role (`roles/docker/tasks/main.yml`)
- **Check Docker installation** before repository setup and package installation

### 6. SQL Role (`roles/sql/tasks/main.yml`)
- **Check DBeaver** before downloading .deb file

## CI Pipeline Optimization

### GitHub Actions Workflow (`.github/workflows/main.yml`)
- **Runs playbook twice consecutively** in each job (Ubuntu and Debian)
- **Adds timing measurements** to show efficiency improvements
- **Clear visual feedback** with emojis and formatting to highlight optimization

## Version Checking Pattern

All version checks follow this pattern:
```yaml
- name: Check if [software] is already installed
  command: [software] --version
  register: [software]_version_check
  failed_when: false
  changed_when: false

- name: [Expensive operation]
  [task details]
  when: [software]_version_check.rc != 0 or [additional conditions]
```

Key points:
- `failed_when: false` - Don't fail if software doesn't exist (expected on first run)
- `changed_when: false` - Don't report version checks as changes
- Use `register` to capture command results
- Use `when` conditions to skip expensive operations when not needed

## Benefits

1. **Faster subsequent runs**: Skip expensive building/downloading when software is already installed
2. **Reduced CI time**: Second run in CI pipeline demonstrates efficiency
3. **System reliability**: System updates always run regardless of package state
4. **Resource efficiency**: Less network bandwidth and CPU time on updates
5. **Better user experience**: Faster local development environment updates

## Testing

The optimization can be tested locally:
```bash
# First run (will install everything)
make provision

# Second run (should be much faster)
make provision
```

Or in CI where both runs happen automatically in each job.

## Requirements Fulfillment

✅ Run ansible script twice in CI pipeline (Ubuntu and Debian)  
✅ Second run is faster due to version checking optimizations  
✅ Check currently installed versions before expensive operations  
✅ System update tasks always run regardless of package state  
✅ Works for both Ubuntu and Debian in CI pipeline  

This addresses todo item #3: "make ansible not re-install software that is already on the desired version"