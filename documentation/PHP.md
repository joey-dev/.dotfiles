## Table of Contents
- [Keybinds](#keybinds)
- [New Project](#new_project)


## Keybinds <a name = "keybinds"></a>

### Auto Complete
- Go down while accepting: `<ctrl>n`
- Go up while accepting: `<ctrl>p`
- Accept highlighted: `<ctrl>y`

### Symbol Navigation
- Show symbol signature: `<leader>ss`
- Go to symbol definition: `<leader>sd`
- Find symbol implementations: `<leader>si`
- Close symbol quick window: `<leader>sq`

### Refactor Navigation
- Refactor - Rename symbol: `<leader>rr`
- Refactor - Format: `<leader>rf`
- Refactor - Change name/namespace to current file name/location: `<leader>rn`
- Refactor - Move class: `<leader>rc`
- Refactor Menu `<leader>rm`

### Generate Navigation
- Generate constructor fields and assign: `<leader>gc`
- Generate methods from implementation/extended classes: `<leader>gm`
- Generate imports: `<leader>gi`
- Generate copy of current class: `<leader>gc`
- Generate new class: `<leader>gn`

### Error and Warning Navigation
- Show all errors/warnings in file: `<leader>ef`
- Open all errors on caret: `<leader>ei`
- Go to next error: `<leader>en`
- Go to previous error: `<leader>ep`

### Debugging
- Toggle Breakpoint: `Alt + b`
- Continue/Start: `Alt + c`
- Step Over: `Alt + o`
- Step Into: `Alt + O`
- See All Symbols Hover: `Alt + s`
- See All Symbols: `Alt + S`
- See Value Under Cursor: `Alt + i`
- Open Cmd for Current Scope: `Alt + t`
- Run to Cursor: `Alt + I`
- Go Back: `Alt + p`
- Continue Back: `Alt + C`
- Toggle Exception Breakpoints: `Alt + E`
- List All Breakpoints: `Alt + l`
- Remove All Breakpoints: `Alt + r`
- Toggle ui: `Alt + u`
    - edit: `e`
    - expand: `Enter`
    - open: `o`
    - delete: `d`
    - toggle: `t`

### Switch between test file and code, and back
- Switch to unit test: `<leader>fut`
- Switch to integration test: `<leader>fit`
- Switch to api test: `<leader>fat`

## New Project <a name = "new_project"></a>

### phpactor
add the following file to the root: `.phpactor.json`
```
{
    "$schema": "/home/joey/.local/share/nvim/mason/packages/phpactor/phpactor.schema.json",
    "logging.enabled": true,
    "logging.level": "debug",
    "logging.path": "phpactor.log",
    "language_server_phpstan.enabled": true, // if you want phpstan enabled
    "language_server_phpstan.bin": "%project_root%\/legacy\/vendor\/bin\/phpstan", // if you want phpstan enabled
    "language_server_phpstan.level": "8", // if you want phpstan enabled
    "phpunit.enabled": true, // if you use phpunit
    "prophecy.enabled": true, // if you use prophecy
    "language_server_php_cs_fixer.enabled": true, // if you want to use pgp cs fixer
    "class_to_file.project_root": "%project_root%\/fileName", // add this if the project is in a mono-repo
    "source_code_filesystem.project_root": "%project_root%\/fileName", // add this if the project is in a mono-repo
    "indexer.project_root": "%project_root%\/fileName", // add this if the project is in a mono-repo
    "composer.autoloader_path": "%project_root%\/fileName\/vendor\/autoload.php", // add this if the project is in a mono-repo
    "symfony.xml_path": "%project_root%\/fileName\/var\/cache\/dev\/App_KernelDevDebugContainer.xml", // add this if the project is in a mono-repo
    "php_code_sniffer.bin": "%project_root%\/fileNAme\/vendor\/bin\/phpcs" // add this if the project is in a mono-repo
}
```

when using phpstan add the phpstan.neon to the root
