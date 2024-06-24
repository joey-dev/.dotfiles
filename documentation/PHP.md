## Table of Contents
- [New Project](#new_project)

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
