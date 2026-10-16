## Table of Contents
- [New Project](#new_project)
- [phpstan-dba (database checks)](#phpstan_dba)

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

## phpstan-dba (database checks) <a name = "phpstan_dba"></a>

phpstan-dba checks your SQL queries against a real database: unknown tables or columns, and the types of the result rows.

The global phpstan config (`~/.config/phpstan_configuration.neon`) always loads `~/.config/phpstan-dba-bootstrap.php`.
That file is the same for every project. It reads the database from the **`PHPSTAN_DBA_URL`** environment variable.

- **Variable set:** phpstan connects to that database and checks the queries.
- **Variable not set:** the query checks are skipped, phpstan runs as normal.

### Set it up for a project

Add the variable to the project's `.envrc` (direnv loads it when you `cd` into the project):

```sh
use flake
export PHPSTAN_DBA_URL="mysql://root:password@127.0.0.1:3306/database_name"
```

- Use the host and port as seen from your laptop, not the Docker service name.
- Special characters in the password must be URL-encoded, for example `@` becomes `%40`.
- Keep `.envrc` out of git (add it to `.git/info/exclude` if the project doesn't ignore it).
- Start Neovim from a shell inside the project, so it gets the variable too.

### When it fails

- **`PHPSTAN_DBA_URL must look like ...`**: the value is not a `mysql://` URL.
- **`Connection refused`**: the database container is not running, or the port is wrong.
