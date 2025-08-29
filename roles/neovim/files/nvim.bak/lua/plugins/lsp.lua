return {
  {
    -- LSP Configuration & Plugins
    'neovim/nvim-lspconfig',
    dependencies = {
      -- Automatically install LSPs to stdpath for neovim
      'williamboman/mason.nvim',
      'williamboman/mason-lspconfig.nvim',
			'nvimtools/none-ls.nvim',
    },
  },

  {
    'williamboman/mason.nvim',
    config = function()
      -- Enable mason
      require('mason').setup()
    end,
  },

  {
    'williamboman/mason-lspconfig.nvim',
    config = function()
      -- This is the table of servers to ensure are installed.
      local ensure_installed = {
        'phpactor',
        'vue-language-server', -- The package name for Volar
        'tsserver', -- TypeScript Language Server
        -- Add any other LSPs you want here
      }

      require('mason-lspconfig').setup {
        ensure_installed = ensure_installed,
      }

      -- Get the on_attach function from your init.lua (or define it here)
      -- This assumes your on_attach function is available globally or required.
      -- For now, we will use a placeholder. We will clean this up in Phase 3.
      local on_attach = function(client, bufnr)
        -- This is where your LSP keymaps from init.lua should go.
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
        -- ...etc
      end

      local capabilities = require('cmp_nvim_lsp').default_capabilities()

      -- Setup language servers.
      local lspconfig = require 'lspconfig'

      -- PHP Setup
      lspconfig.phpactor.setup {
        capabilities = capabilities,
        on_attach = on_attach,
      }

      -- Vue / TypeScript Setup
      lspconfig.volar.setup {
        capabilities = capabilities,
        on_attach = on_attach,
        filetypes = { 'typescript', 'javascript', 'javascriptreact', 'typescriptreact', 'vue' },
        -- This uses the special tsconfig we created earlier
        root_dir = lspconfig.util.root_pattern('package.json'),
        init_options = {
          typescript = {
            tsdk = 'node_modules/typescript/lib',
            configFileName = 'tsconfig.neovim.json' -- Your stricter config
          }
        }
      }
    end,
  },
}
