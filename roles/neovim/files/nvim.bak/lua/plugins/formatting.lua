return {
  {
    "nvimtools/none-ls.nvim",
    config = function()
      -- THE FIX: Manually add this plugin's path to Lua's package.path
      -- This is a workaround for lazy.nvim failing to do so in your environment.
      local plugin_path = vim.fn.stdpath("data") .. "/lazy/none-ls.nvim"
      package.path = package.path .. ";" .. plugin_path .. "/lua/?.lua"

      -- Now, attempt to load the module
      local ok, none_ls = pcall(require, "none-ls")

      if not ok then
        vim.notify("Could not require none-ls even after manually setting path.", vim.log.levels.ERROR)
        return
      end

      -- If we get here, the setup can proceed
      none_ls.setup({
        sources = {
          none_ls.builtins.formatting.phpcsfixer,
          none_ls.builtins.diagnostics.phpstan,
          none_ls.builtins.formatting.prettier,
          none_ls.builtins.diagnostics.eslint,
        },
      })

      vim.keymap.set("n", "<leader>gf", vim.lsp.buf.format, { desc = "[G]o [F]ormat" })
    end,
  },
}
