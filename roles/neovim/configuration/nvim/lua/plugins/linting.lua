-- ~/.config/nvim/lua/plugins/lint.lua
return {
  {
    "mfussenegger/nvim-lint",
    -- This is the key fix: Explicitly tell LazyVim this plugin creates the "Lint" command.
    -- This forces the plugin to load when you try to use the command.
    cmd = { "Lint", "LintToggle" },
    -- Use the standard 'opts' table for configuration. This is the correct way.
    opts = {
      linters_by_ft = {
        php = { "phpstan" },
      },
      linters = {
        phpstan = {
          cmd = "/home/joey/.config/composer/vendor/bin/phpstan",
          args = {
            "analyse",
            "--level=8",
            "-a",
            "vendor/autoload.php",
            "-c",
            "phpstan.neon",
            "--error-format=raw",
            "--no-progress",
            "$file",
          },
        },
      },
    },
  },
}
