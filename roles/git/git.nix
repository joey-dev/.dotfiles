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
    # userName and userEmail should be set per-user
    # These can be configured in the user's home-manager configuration
    settings = {
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
  };
}
