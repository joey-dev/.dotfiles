-- Keymaps are automatically loaded on the VeryLazy event
-- Default keymaps that are always set: https://github.com/LazyVim/LazyVim/blob/main/lua/lazyvim/config/keymaps.lua
-- Add any additional keymaps here

local map = LazyVim.safe_keymap_set

map("n", "<M-q>", "<cmd>bprevious<cr>", { desc = "Prev Buffer" })
map("n", "<M-e>", "<cmd>bnext<cr>", { desc = "Next Buffer" })
map("n", "<M-w>", function()
  Snacks.bufdelete()
end, { desc = "Delete Buffer" })

map("n", "<Leader>ci", function()
  -- Get the Phpactor LSP client specifically
  local phpactor_client = vim.lsp.get_active_clients({ bufnr = 0, name = 'phpactor' })[1]

  if not phpactor_client then
    vim.notify("Phpactor LSP client not active for this buffer.", vim.log.levels.WARN)
    return
  end

  local uri = vim.uri_from_bufnr(0)

  -- Execute the Phpactor command, targeting only the Phpactor client
  phpactor_client.request("workspace/executeCommand", {
    command = "import_all_unresolved_names",
    arguments = { uri },
  })
end, { desc = 'Generate imports' })
