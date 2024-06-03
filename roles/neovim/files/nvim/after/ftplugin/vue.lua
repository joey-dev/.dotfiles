local vim = vim
local execute = vim.api.nvim_command
local fn = vim.fn
local lsp = require("lsp-zero")
local util = require 'lspconfig.util'

vim.o.tabstop = 2
vim.o.softtabstop = 2
vim.o.shiftwidth = 2
vim.o.expandtab = true

vim.api.nvim_create_autocmd('LspAttach', {
  desc = 'LSP actions',
  callback = function(event)
    local opts = {buffer = event.buf}

    vim.keymap.set('n', '<leader>ss', '<cmd>lua vim.lsp.buf.hover()<cr>', opts)
    vim.keymap.set('n', '<leader>sd', '<cmd>lua vim.lsp.buf.definition()<cr>', opts)
    vim.keymap.set('n', '<leader>si', '<cmd>lua vim.lsp.buf.references()<cr>', opts)
    vim.keymap.set('n', '<leader>rr', '<cmd>lua vim.lsp.buf.rename()<cr>', opts)
    vim.keymap.set('n', '<leader>rf', '<cmd>lua vim.lsp.buf.format({async = true})<cr>', opts)
    vim.keymap.set('n', '<leader>ef', '<cmd>lua vim.lsp.buf.code_action()<cr>', opts)
    vim.keymap.set('n', '<leader>ei', '<cmd>lua vim.diagnostic.open_float()<cr>', opts)
    vim.keymap.set('n', '<leader>en', '<cmd>lua vim.diagnostic.goto_prev()<cr>', opts)
    vim.keymap.set('n', '<leader>ep', '<cmd>lua vim.diagnostic.goto_next()<cr>', opts) 
    vim.keymap.set('n', '<leader>sq', ':cclose<CR>', opts) 
  end
})

vim.b.ale_linter_aliases = {'css', 'javascript', 'vue', 'typescript'}

vim.b.ale_linters = {'eslint'}

require('mason').setup({})
require("mason-lspconfig").setup({
    ensure_installed = {"volar"},
})

local lspconfig = require'lspconfig'
local lspconfig_configs = require'lspconfig.configs'
local lspconfig_util = require 'lspconfig.util'

local function find_node_module_path()
	local path1 = '/usr/local/lib/node_modules/typescript/lib'
    local path2 = '/usr/lib/node_modules/typescript/lib'

    if vim.fn.isdirectory(path1) == 1 then
        return path1
    elseif vim.fn.isdirectory(path2) == 1 then
        return path2
    else
        return nil
    end
end

local volar_cmd = {'vue-language-server', '--stdio'}
local volar_root_dir = lspconfig_util.root_pattern 'package.json'

lspconfig_configs.volar_api = {
  default_config = {
    cmd = volar_cmd,
    root_dir = volar_root_dir,
	on_new_config = function(new_config, new_root_dir)
	  new_config.init_options.typescript.tsdk = find_node_module_path()
	end,
    filetypes = { 'vue'},
    -- If you want to use Volar's Take Over Mode (if you know, you know)
    --filetypes = { 'typescript', 'javascript', 'javascriptreact', 'typescriptreact', 'vue', 'json' },
    init_options = {
      typescript = {
        tsdk = ''
      },
      languageFeatures = {
        implementation = true, -- new in @volar/vue-language-server v0.33
        references = true,
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
          getDocumentNameCasesRequest = false,
          getDocumentSelectionRequest = false,
        },
      }
    },
  }
}

lspconfig_configs.volar_doc = {
  default_config = {
    cmd = volar_cmd,
    root_dir = volar_root_dir,
	on_new_config = function(new_config, new_root_dir)
	  new_config.init_options.typescript.tsdk = find_node_module_path()
	end,

    filetypes = { 'vue'},
    -- If you want to use Volar's Take Over Mode (if you know, you know):
    filetypes = { 'typescript', 'javascript', 'javascriptreact', 'typescriptreact', 'vue', 'json' },
    init_options = {
      typescript = {
        tsdk = ''
      },
      languageFeatures = {
        implementation = true, -- new in @volar/vue-language-server v0.33
        documentHighlight = true,
        documentLink = true,
        codeLens = { showReferencesNotification = true},
        -- not supported - https://github.com/neovim/neovim/pull/15723
        semanticTokens = false,
        diagnostics = true,
        schemaRequestService = true,
      }
    },
  }
}

lspconfig_configs.volar_html = {
  default_config = {
    cmd = volar_cmd,
    root_dir = volar_root_dir,
	on_new_config = function(new_config, new_root_dir)
	  new_config.init_options.typescript.tsdk = find_node_module_path()
	end,

    filetypes = { 'vue'},
    -- If you want to use Volar's Take Over Mode (if you know, you know), intentionally no 'json':
    --filetypes = { 'typescript', 'javascript', 'javascriptreact', 'typescriptreact', 'vue' },
    init_options = {
      typescript = {
        tsdk = ''
      },
      documentFeatures = {
        selectionRange = true,
        foldingRange = true,
        linkedEditingRange = true,
        documentSymbol = true,
        -- not supported - https://github.com/neovim/neovim/pull/13654
        documentColor = false,
        documentFormatting = {
          defaultPrintWidth = 100,
        },
      }
    },
  }
}
lspconfig.volar.setup{}

-- debug
local dap = require('dap')

require("dap-vscode-js").setup({
  node_path = "node", -- Path of node executable. Defaults to $NODE_PATH, and then "node"
  debugger_path = vim.fn.stdpath('data') .. "/lazy/vscode-js-debug",
  -- debugger_cmd = { "extension" }, -- Command to use to launch the debug server. Takes precedence over `node_path` and `debugger_path`.
  adapters = { 'chrome', 'pwa-node', 'pwa-chrome', 'pwa-msedge', 'node-terminal', 'pwa-extensionHost', 'node', 'chrome' }, -- which adapters to register in nvim-dap
  -- log_file_path = "(stdpath cache)/dap_vscode_js.log" -- Path for file logging
  -- log_file_level = false -- Logging level for output to file. Set to false to disable file logging.
  -- log_console_level = vim.log.levels.ERROR -- Logging level for output to console. Set to false to disable console output.
})

local js_based_languages = { "typescript", "javascript", "typescriptreact", "vue" }

for _, language in ipairs(js_based_languages) do
  require("dap").configurations[language] = {
    {
      type = "pwa-node",
      request = "launch",
      name = "Launch file",
      program = "${file}",
      cwd = "${workspaceFolder}",
    },
    {
      type = "pwa-node",
      request = "attach",
      name = "Attach",
      processId = require 'dap.utils'.pick_process,
      cwd = "${workspaceFolder}",
    },
    {
      type = "pwa-chrome",
      request = "launch",
      name = "Start Chrome with \"localhost\"",
      url = "http://localhost:3000",
      webRoot = "${workspaceFolder}",
      userDataDir = "${workspaceFolder}/.vscode/vscode-chrome-debug-userdatadir"
    }
  }
end

vim.api.nvim_set_keymap('n', '<A-b>', ":lua require'dap'.toggle_breakpoint()<CR>", { noremap = true, silent = true, nowait = false })
vim.api.nvim_set_keymap('n', '<A-c>', ":lua require'dap'.continue()<CR>", { noremap = true, silent = true, nowait = false })
vim.api.nvim_set_keymap('n', '<A-o>', ":lua require'dap'.step_over()<CR>", { noremap = true, silent = true, nowait = false })
vim.api.nvim_set_keymap('n', '<A-O>', ":lua require'dap'.step_into()<CR>", { noremap = true, silent = true, nowait = false })
vim.api.nvim_set_keymap('n', '<A-s>', ":lua OpenDebugWidget()<CR>", { noremap = true, silent = true, nowait = false })
vim.api.nvim_set_keymap('n', '<A-S>', ":lua OpenDebugWidgetInWindow()<CR>", { noremap = true, silent = true, nowait = false })
vim.api.nvim_set_keymap('n', '<A-i>', ":lua require'dap.ui.widgets'.hover()<CR>", { noremap = true, silent = true, nowait = false })
vim.api.nvim_set_keymap('n', '<A-t>', ":lua require'dap'.repl.open()<CR>", { noremap = true, silent = true, nowait = false })
vim.api.nvim_set_keymap('n', '<A-I>', ":lua require'dap'.run_to_cursor()<CR>", { noremap = true, silent = true, nowait = false })
vim.api.nvim_set_keymap('n', '<A-p>', ":lua require'dap'.step_back()<CR>", { noremap = true, silent = true, nowait = false })
vim.api.nvim_set_keymap('n', '<A-C>', ":lua require'dap'.reverse_continue()<CR>", { noremap = true, silent = true, nowait = false })
vim.api.nvim_set_keymap('n', '<A-E>', ":lua require'dap'.set_exception_breakpoints()<CR>", { noremap = true, silent = true, nowait = false })
vim.api.nvim_set_keymap('n', '<A-l>', ":lua require'dap'.list_breakpoints()<CR>", { noremap = true, silent = true, nowait = false })
vim.api.nvim_set_keymap('n', '<A-r>', ":lua require'dap'.clear_breakpoints()<CR>", { noremap = true, silent = true, nowait = false })
vim.keymap.set('n', '<leader>B', function()
  require 'dap'.set_breakpoint(vim.fn.input('Breakpoint condition: '))
end)


function OpenDebugWidget()
  local widgets = require('dap.ui.widgets')
  widgets.centered_float(widgets.scopes)
end

function OpenDebugWidgetInWindow()
  local widgets = require('dap.ui.widgets')
  local my_sidebar = widgets.sidebar(widgets.scopes)
  my_sidebar.open()
end

