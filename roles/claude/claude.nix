{ pkgs, ... }:

{

  home.packages = with pkgs; [
    claude-code
    jq
    libnotify
  ];

  home.file.".claude" = {
    source = ./configuration;
    recursive = true;
  };

}
