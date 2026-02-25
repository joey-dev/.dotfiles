{ config, pkgs, ... }:

{
  # Git is typically already installed in NixOS, but we ensure it here
  home.packages = with pkgs; [
    git
    git-lfs
    meld  # Git merge tool
  ];

  # Git configuration
  programs.git = {
    enable = true;
    
    extraConfig = {
      core = {
        editor = "nvim";
      };
      init = {
        defaultBranch = "master";
      };
      merge = {
        tool = "meld";
      };
      mergetool = {
        meld = {
          cmd = ''meld "$LOCAL" "$MERGED" "$REMOTE" --output "$MERGED"'';
          keepBackup = false;
        };
      };
    };
    
    # Include ~/.gitconfig.local for personal settings (userName, userEmail, etc.)
    includes = [{ path = "~/.gitconfig.local"; }];
  };
}