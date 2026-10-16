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

    # Syntax-highlighted diffs in git
    programs.delta = {
      enable = true;
      enableGitIntegration = true;
    };

    programs.lazygit = {
      enable = true;
      settings.customCommands = [
        {
          key = "<c-c>";
          context = "files";
          description = "Commit with message starting with ticket";
          prompts = [
            {
              type = "input";
              title = "Add Commit Message";
              key = "Message";
            }
          ];
          # Branch `ABC-123-some-name` gives the message `[ABC-123] <message>`
          command = ''git commit -m "$(git branch --contains | awk -v m="{{.Form.Message}}" ' /\*/{split($2, n, /-/); print ("["n[1] "-" n[2] "] " m)}')"'';
          output = "terminal";
        }
      ];
    };
  };
}
