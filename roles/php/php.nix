{
  config,
  lib,
  pkgs,
  ...
}:

let
  # Latest PHP, for quick scripts. Projects bring their own PHP through their flake.
  inherit (pkgs) php;
  inherit (php.packages) composer;

  composerHome = "${config.xdg.configHome}/composer";

  # Fill in the paths the PHP config files need
  withPaths = file: {
    text =
      builtins.replaceStrings
        [ "@composerHome@" "@stubs@" "@dbaBootstrap@" ]
        [
          composerHome
          "${./configuration/phpstan_stubs}"
          "${config.xdg.configHome}/phpstan-dba-bootstrap.php"
        ]
        (builtins.readFile file);
  };
in
{
  options.roles.php.enable = lib.mkEnableOption "the php role";

  config = lib.mkIf config.roles.php.enable {
    home.packages = [
      php
      composer
      pkgs.phpactor
      php.packages.phpmd
      php.packages.psalm
      pkgs.vscode-extensions.xdebug.php-debug
    ];

    home.sessionVariables = {
      COMPOSER_HOME = composerHome;
    };

    home.sessionPath = [
      "${composerHome}/vendor/bin"
    ];

    xdg.configFile = {
      # Global composer packages (phpstan and its extensions)
      "composer/composer.json".source = ./global-composer/composer.json;
      "composer/composer.lock".source = ./global-composer/composer.lock;

      # PHP tool configuration
      "phpmd_ruleset.xml".source = ./configuration/phpmd_ruleset.xml;
      "phpstan_configuration.neon" = withPaths ./configuration/phpstan_configuration.neon;
      # Takes the database from PHPSTAN_DBA_URL, see documentation/PHP.md
      "phpstan-dba-bootstrap.php" = withPaths ./configuration/phpstan-dba-bootstrap.php;
      "phpstan_stubs".source = ./configuration/phpstan_stubs;
      "phpactor/phpactor.json".source = ./configuration/phpactor.json;
    };

    # Install the global composer packages, exactly as pinned in composer.lock
    home.activation.installGlobalComposerPackages = lib.hm.dag.entryAfter [ "writeBoundary" ] ''
      export PATH="${php}/bin:${composer}/bin:$PATH"
      export COMPOSER_HOME="${composerHome}"
      run composer global install --no-interaction --quiet
    '';
  };
}
