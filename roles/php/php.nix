{ config, pkgs, ... }:

{
  home.packages = with pkgs; [
    php83
    php83Packages.composer
    phpactor
    php83Packages.phpmd
    php83Packages.psalm
    vscode-extensions.xdebug.php-debug
  ];

  home.sessionVariables = {
    COMPOSER_HOME = "$HOME/.config/composer";
  };

  home.sessionPath = [
    "$HOME/.config/composer/vendor/bin"
  ];

  # Symlink your tracked files from your dotfiles directly into Composer's home
  home.file.".config/composer/composer.json".source = ./global-composer/composer.json;
  home.file.".config/composer/composer.lock".source = ./global-composer/composer.lock;

  # The Activation Hook: Now runs 'install' instead of 'update'
  home.activation.installGlobalComposerPackages = config.lib.dag.entryAfter ["writeBoundary"] ''
    export PATH="${pkgs.php83}/bin:${pkgs.php83Packages.composer}/bin:$PATH"
    
    # Run 'install' so it strictly respects your tracked composer.lock file
    $DRY_RUN_CMD composer global install --no-interaction --quiet
  '';
}
