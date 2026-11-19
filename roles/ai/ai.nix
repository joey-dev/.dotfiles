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

        dependencies = [ python3Packages.jsonschema ];

        nativeCheckInputs = [
          python3Packages.pytestCheckHook
          git
        ];

        nativeBuildInputs = [ makeWrapper ];

        # The config schema lives outside src; the config tests read it from here.
        preCheck = ''
          export CLAUDE_WORKFLOW_SCHEMA=${./configuration/workflows/config/config.schema.json}
        '';

        postInstall = ''
          mkdir -p $out/share/claude-workflow
          cp -r $src/skills $out/share/claude-workflow/skills
          # Fallback when the config dir has no config.schema.json.
          cp ${./configuration/workflows/config/config.schema.json} $out/share/claude-workflow/config.schema.json
        '';

        postFixup = ''
          wrapProgram $out/bin/claude-workflow \
            --prefix PATH : ${
              lib.makeBinPath [
                bubblewrap
                git
                libnotify
                claude-code
                socat
              ]
            } \
            --set-default CLAUDE_WORKFLOW_SKILLS $out/share/claude-workflow/skills \
            --set-default CLAUDE_WORKFLOW_SCHEMA $out/share/claude-workflow/config.schema.json
        '';
      })
    ];

    home.file.".claude" = {
      source = ./configuration/claude;
      recursive = true;
    };

    # Skills come from the package (CLAUDE_WORKFLOW_SKILLS in the wrapper above).
    # global.config.json, repository/<repo-name>.config.json and the schema (see docs/11).
    xdg.configFile."claude-workflow".source = ./configuration/workflows/config;
  };
}
