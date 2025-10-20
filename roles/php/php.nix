{ config, pkgs, ... }:

{
  # Install PHP and related tools
  home.packages = with pkgs; [
    php83
    php83Packages.composer
    
    # PHP development tools
    phpactor
    phpstan
    php83Packages.phpmd
    php83Packages.psalm
  ];

  # PHP configuration
  home.sessionVariables = {
    COMPOSER_HOME = "$HOME/.config/composer";
  };

  home.sessionPath = [
    "$HOME/.config/composer/vendor/bin"
  ];
}
