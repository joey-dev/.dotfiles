{
  config,
  lib,
  pkgs,
  ...
}:

{
  options.roles.git.enable = lib.mkEnableOption "the git role";

  config = lib.mkIf config.roles.git.enable {
    home.packages = with pkgs; [
      meld # Git merge tool
    ];

    # Git configuration
    programs.git = {
      enable = true;
      lfs.enable = true;

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

      # Include ~/.gitconfig.local for personal settings (userName, userEmail, etc.)
      includes = [ { path = "~/.gitconfig.local"; } ];
    };
  };
}
