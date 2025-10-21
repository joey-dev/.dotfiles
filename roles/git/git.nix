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
    # userName and userEmail can be set in a separate git_private.nix file
    # Create ~/.git_private.nix with:
    # {
    #   programs.git = {
    #     userName = "Your Name";
    #     userEmail = "your.email@example.com";
    #   };
    # }
    # The home.nix file will automatically import it if it exists
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
