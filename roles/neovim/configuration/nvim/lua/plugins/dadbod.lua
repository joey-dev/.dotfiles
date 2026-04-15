return {
  -- ==========================================
  -- 1. THE DADBOD CORE AND UI
  -- ==========================================
  {
    "kristijanhusak/vim-dadbod-ui",
    dependencies = {
      { "tpope/vim-dadbod", lazy = true },
      { "kristijanhusak/vim-dadbod-completion", ft = { "sql", "mysql", "plsql" }, lazy = true },
    },
    cmd = { "DBUI", "DBUIToggle", "DBUIAddConnection", "DBUIFindBuffer" },
    init = function()
      vim.g.db_ui_save_location = vim.fn.stdpath("data") .. "/db_ui"
      vim.g.db_ui_use_nerd_fonts = 1

      local secrets_file = vim.fn.expand("~/.local/share/nvim/db_secrets.json")
      if vim.fn.filereadable(secrets_file) == 1 then
        local raw_json = vim.fn.readfile(secrets_file)
        local success, secrets = pcall(vim.fn.json_decode, raw_json)

        if success and secrets.password and secrets.databases then
          local base_url = string.format("mysql://root:%s@127.0.0.1:3306/", secrets.password)
          local dbs = {}
          for _, db_name in ipairs(secrets.databases) do
            dbs[db_name] = base_url .. db_name
          end
          vim.g.dbs = dbs
        end
      end
    end,
  },

  -- ==========================================
  -- 2. THE AUTOCOMPLETE HOOK (For modern LazyVim using Blink)
  -- ==========================================
  {
    "saghen/blink.cmp",
    optional = true,
    dependencies = { "kristijanhusak/vim-dadbod-completion" },
    opts = {
      sources = {
        per_filetype = {
          -- We must explicitly include lsp, snippets, and buffer so we don't break standard autocomplete!
          sql = { "dadbod", "lsp", "snippets", "buffer" },
          mysql = { "dadbod", "lsp", "snippets", "buffer" },
          plsql = { "dadbod", "lsp", "snippets", "buffer" },
        },
        providers = {
          dadbod = {
            name = "Dadbod",
            module = "vim_dadbod_completion.blink",
            score_offset = 100, -- Give database tables/columns top priority!
          },
        },
      },
    },
  },
}
