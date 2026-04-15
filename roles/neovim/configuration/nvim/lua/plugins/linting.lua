local current_dir = vim.fn.getcwd()
local is_legacy = vim.fn.isdirectory(current_dir .. "/legacy") == 1

local autoload_path = is_legacy and "legacy/vendor/autoload.php" or "vendor/autoload.php"
local config_path = is_legacy and "legacy/phpstan.neon" or "phpstan.neon"

return {
  {
    "mfussenegger/nvim-lint",
    opts = function(_, opts)
      opts.linters_by_ft = {
        php = { "phpstan" },
        sql = { "sqlfluff" },
        mysql = { "sqlfluff" },
      }

      -- Grab the default parser to wrap it
      local default_parser = require("lint.linters.phpstan").parser

      opts.linters = opts.linters or {}
      opts.linters.phpstan = {
        args = {
          "analyse",
          "-a",
          autoload_path,
          "-c",
          config_path,
          "--memory-limit=2G",
          "--error-format=json",
          "--no-progress",
        },
        -- The JSON Sanitizer: Strips PHP warnings so Neovim doesn't crash
        parser = function(output, bufnr)
          local json_start = string.find(output, "{")
          if json_start then
            output = string.sub(output, json_start)
          end
          return default_parser(output, bufnr)
        end,
      }

      opts.linters.sqlfluff = {
        args = {
          "lint",
          "--format=json",
          "--dialect=mysql",
          "-",
        },
      }

      return opts
    end,
  },
}
