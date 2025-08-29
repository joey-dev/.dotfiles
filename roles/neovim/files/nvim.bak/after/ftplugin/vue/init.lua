local vim = vim
local execute = vim.api.nvim_command
local fn = vim.fn
local lsp = require("lsp-zero")
local util = require 'lspconfig.util'

vim.o.tabstop = 2
vim.o.softtabstop = 2
vim.o.shiftwidth = 2
vim.o.expandtab = true

--[[
vim.api.nvim_create_autocmd('LspAttach', {
  desc = 'LSP actions',
  callback = function(event)
    local opts = {buffer = event.buf}

    vim.keymap.set('n', '<leader>ss', '<cmd>lua vim.lsp.buf.hover()<cr>', opts)
    vim.keymap.set('n', '<leader>sd', '<cmd>lua vim.lsp.buf.definition()<cr>', opts)
    vim.keymap.set('n', '<leader>si', '<cmd>lua vim.lsp.buf.references()<cr>', opts)
    vim.keymap.set('n', '<leader>rr', '<cmd>lua vim.lsp.buf.rename()<cr>', opts)
    vim.keymap.set('n', '<leader>rf', '<cmd>lua vim.lsp.buf.format({async = true})<cr>', opts)
    vim.keymap.set('n', '<leader>ei', '<cmd>lua vim.diagnostic.open_float()<cr>', opts)
    vim.keymap.set('n', '<leader>en', '<cmd>lua vim.diagnostic.goto_prev()<cr>', opts)
    vim.keymap.set('n', '<leader>ep', '<cmd>lua vim.diagnostic.goto_next()<cr>', opts)
    vim.keymap.set('n', '<leader>sq', ':cclose<CR>', opts)
  end
})
--]]

vim.b.ale_linter_aliases = {'css', 'javascript', 'vue', 'typescript'}

vim.b.ale_linters = {'eslint'}


vim.b.ale_fixers = {'eslint', 'prettier'}
vim.b.ale_fix_on_save = 1

require('mason').setup({})
-- require("mason-lspconfig").setup({
    -- ensure_installed = {"vue-language-server"},
-- })

-- It's good practice to have your LSP configs in a dedicated file
-- like lua/your-name/lsp.lua and call it from your init.lua

local lspconfig = require('lspconfig')
local on_attach = function(client, bufnr)
  -- This is a standard on_attach function.
  -- You can add your keymaps for LSP features here.
  -- For example:
  local nmap = function(keys, func, desc)
    if desc then
      desc = 'LSP: ' .. desc
    end
    vim.keymap.set('n', keys, func, { buffer = bufnr, noremap = true, silent = true, desc = desc })
  end

  nmap('<leader>rn', vim.lsp.buf.rename, '[R]e[n]ame')
  nmap('<leader>ca', vim.lsp.buf.code_action, '[C]ode [A]ction')
  nmap('gd', vim.lsp.buf.definition, '[G]oto [D]efinition')
  nmap('gr', require('telescope.builtin').lsp_references, '[G]oto [R]eferences')
  nmap('gI', vim.lsp.buf.implementation, '[G]oto [I]mplementation')
  nmap('K', vim.lsp.buf.hover, 'Hover Documentation')
  nmap('<leader>ws', vim.lsp.buf.workspace_symbol, '[W]orkspace [S]ymbols')

  -- This is the key part for diagnostics
  -- It enables error highlighting in the gutter (the column on the left)
  vim.diagnostic.config({
    virtual_text = true, -- Show errors inline
    signs = true,
    underline = true,
    update_in_insert = false,
  })
end


-- Main Volar Configuration
lspconfig.volar.setup({
  -- The on_attach function is where you configure keymaps
  -- and what happens when the LSP attaches to a buffer.
  on_attach = on_attach,

  -- filetypes tells the LSP which files to attach to.
  -- If you ONLY want Volar for .vue files, use: { 'vue' }
  -- For "Take Over Mode" (recommended), let Volar handle JS/TS as well.
  -- This gives you Vue-aware intellisense in your TS files.
  filetypes = {'typescript', 'javascript', 'javascriptreact', 'typescriptreact', 'vue'},

	root_dir = function(fname)
    -- Find the project root with package.json or .git
    local root = util.root_pattern('package.json', '.git')(fname)

    -- If a root is found, check for a 'frontend' sub-directory
    if root then
      local frontend_root = root .. '/frontend'
      -- If that 'frontend' directory exists, use it as the new root.
      if vim.fn.isdirectory(frontend_root) == 1 then
        return frontend_root
      end
      -- Otherwise, fall back to the detected project root.
      return root
    end
    -- Return nil if no root was found
    return nil
  end,

  -- The init_options section is crucial.
  init_options = {
    -- This enables the "languageFeatures" that provide diagnostics (errors).
    languageFeatures = {
        diagnostics = true,
        -- You can keep other features you had enabled here.
        references = true,
        implementation = true,
        definition = true,
        typeDefinition = true,
        callHierarchy = true,
        hover = true,
        rename = true,
        renameFileRefactoring = true,
        signatureHelp = true,
        codeAction = true,
        workspaceSymbol = true,
        completion = {
            defaultTagNameCase = 'kebabCase',
            defaultAttrNameCase = 'kebabCase',
        },
    },
    -- This enables features for the document itself, like formatting.
    documentFeatures = {
        documentFormatting = {
            defaultPrintWidth = 100,
        },
    },
    -- This tells Volar where to find the TypeScript version
    -- that your project is using. This is critical for correct type-checking.
    typescript = {
      tsdk = 'node_modules/typescript/lib',
			configFileName = 'tsconfig.neovim.json'
    }
  }
})
