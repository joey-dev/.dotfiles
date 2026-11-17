{
  config,
  lib,
  pkgs,
  ...
}:

{
  options.roles.ai.enable = lib.mkEnableOption "the ai role";

  config = lib.mkIf config.roles.ai.enable {
    home.packages = with pkgs; [
      claude-code
      codex
      jq
      libnotify
      bubblewrap

      (python3Packages.buildPythonApplication {
        pname = "claude-workflow";
        version = "0.1.0";
        pyproject = true;
        src = ./configuration/workflows/workflow;

        build-system = [ python3Packages.setuptools ];

        nativeCheckInputs = [
          python3Packages.pytestCheckHook
          git
        ];

        makeWrapperArgs = [
          "--prefix PATH : ${lib.makeBinPath [ bubblewrap git libnotify claude-code ]}"
          "--set-default CLAUDE_WORKFLOW_SKILLS ${placeholder "out"}/share/claude-workflow/skills"
        ];

        postInstall = ''
          mkdir -p $out/share/claude-workflow
          cp -r $src/skills $out/share/claude-workflow/skills
        '';
      })
    ];

    home.file.".claude" = {
      source = ./configuration/claude;
      recursive = true;
    };
  };
}
