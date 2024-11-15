local vim = vim
local execute = vim.api.nvim_command
local fn = vim.fn
local lsp = require("lsp-zero")

vim.o.tabstop = 2
vim.o.softtabstop = 2
vim.o.shiftwidth = 2
vim.o.expandtab = true

-- init.lua
lsp.preset('recommended')

-- Mason setup
require('mason').setup()
require('mason-lspconfig').setup({
    ensure_installed = { 'ts_ls' },
})

-- nvim-cmp setup
local cmp = require('cmp')
local cmp_select = {behavior = cmp.SelectBehavior.Select}
local cmp_mappings = {
  ['<C-p>'] = cmp.mapping.select_prev_item(cmp_select),
  ['<C-n>'] = cmp.mapping.select_next_item(cmp_select),
  ['<C-y>'] = cmp.mapping.confirm({ select = true }),
  ['<C-Space>'] = cmp.mapping.complete(),
}

cmp.setup({
  mapping = cmp_mappings,
  sources = {
    { name = 'nvim_lsp' },
    -- Add other sources as needed
  },
})

-- Setup LSP
lsp.on_attach(function(client, bufnr)
  local opts = { buffer = bufnr, remap = false }

  vim.keymap.set("n", "<leader>sd", vim.lsp.buf.definition, opts)
  vim.keymap.set("n", "<leader>ss", vim.lsp.buf.hover, opts)
  vim.keymap.set("n", "<leader>sf", vim.lsp.buf.workspace_symbol, opts) -- rename
  vim.keymap.set("n", "<leader>ei", vim.diagnostic.open_float, opts)
  vim.keymap.set("n", "<leader>en", vim.diagnostic.goto_next, opts)
  vim.keymap.set("n", "<leader>ep", vim.diagnostic.goto_prev, opts)
  vim.keymap.set("n", "<leader>rm", vim.lsp.buf.code_action, opts)
  vim.keymap.set("n", "<leader>si", vim.lsp.buf.references, opts)
  vim.keymap.set("n", "<leader>rr", vim.lsp.buf.rename, opts)
  vim.keymap.set("n", "<leader>ra", vim.lsp.buf.signature_help, opts)
  vim.keymap.set('n', '<leader>sq', ':cclose<CR>', opts)
end)

lsp.setup()

-- Optional: Diagnostic keymaps
vim.diagnostic.config({
  virtual_text = true,
  signs = true,
  update_in_insert = true,
  underline = true,
  severity_sort = false,
  float = true,
})

-- Additional LSP configurations
local lspconfig = require('lspconfig')
lspconfig.ts_ls.setup{}

-------

vim.b.ale_linter_aliases = {'css', 'javascript', 'vue', 'typescript'}
vim.b.ale_linters = {'eslint'}
vim.g.ale_root = '/home/joey/Code/Work/dyflexis-monorepo/frontend'

