-- wanted:
-- PhpactorExtractExpression
-- PhpactorExtractMethod

local vim = vim
local execute = vim.api.nvim_command
local fn = vim.fn
local lsp = require("lsp-zero")

-- keybinds
vim.api.nvim_set_keymap('n', '<leader>rn', ':lua RunPhpactorRefactorCommand("fix_namespace_class_name")<CR>', { noremap = true, silent = true, nowait = false }) -- needs testing
vim.api.nvim_set_keymap('n', '<leader>gf', ':lua RunPhpactorRefactorCommand("complete_constructor")<CR>', { noremap = true, silent = true, nowait = false })
vim.api.nvim_set_keymap('n', '<leader>gm', ':lua RunPhpactorRefactorCommand("implement_contracts")<CR>', { noremap = true, silent = true, nowait = false }) -- needs testing
vim.api.nvim_set_keymap('n', '<leader>rm', ":lua require('phpactor').rpc('context_menu', {})<CR>", { noremap = true, silent = true, nowait = false })
vim.api.nvim_set_keymap('v', '<leader>rm', ":lua require('phpactor').rpc('context_menu', {})<CR>", { noremap = true, silent = true, nowait = false })
vim.api.nvim_set_keymap('n', '<leader>gi', ":lua require('phpactor').rpc('import_missing_classes', {})<CR>", { noremap = true, silent = true, nowait = false })
vim.api.nvim_set_keymap('n', '<leader>gc', ":lua require('phpactor').rpc('copy_class', {})<CR>", { noremap = true, silent = true, nowait = false })
vim.api.nvim_set_keymap('n', '<leader>gn', ":lua require('phpactor').rpc('new_class', {})<CR>", { noremap = true, silent = true, nowait = false })
vim.api.nvim_set_keymap('n', '<leader>rc', ":lua require('phpactor').rpc('move_class', {})<CR>", { noremap = true, silent = true, nowait = false })

vim.api.nvim_create_autocmd('LspAttach', {
  desc = 'LSP actions',
  callback = function(event)
    local opts = {buffer = event.buf}

    vim.keymap.set('n', '<leader>ss', '<cmd>lua vim.lsp.buf.hover()<cr>', opts)
    vim.keymap.set('n', '<leader>sd', '<cmd>lua vim.lsp.buf.definition()<cr>', opts)
    vim.keymap.set('n', '<leader>si', '<cmd>lua vim.lsp.buf.references()<cr>', opts)
    vim.keymap.set('n', '<leader>rr', '<cmd>lua vim.lsp.buf.rename()<cr>', opts)
    vim.keymap.set({'n', 'x'}, '<leader>rf', '<cmd>lua vim.lsp.buf.format({async = true})<cr>', opts)
    vim.keymap.set('n', '<leader>ef', '<cmd>lua vim.lsp.buf.code_action()<cr>', opts)
    vim.keymap.set('n', '<leader>ei', '<cmd>lua vim.diagnostic.open_float()<cr>', opts)
    vim.keymap.set('n', '<leader>en', '<cmd>lua vim.diagnostic.goto_prev()<cr>', opts)
    vim.keymap.set('n', '<leader>ep', '<cmd>lua vim.diagnostic.goto_next()<cr>', opts) 
    vim.keymap.set('n', '<leader>sq', ':cclose<CR>', opts) 
  end
})

vim.g.ale_linters = {php = {'phpmd', 'phpstan'}}

-- phpmd
vim.g.ale_php_phpmd_executable = os.getenv("HOME") .. '/.config/composer/vendor/bin/phpmd'
vim.g.ale_php_phpmd_ruleset = os.getenv("HOME") .. '/.dotfiles/roles/neovim/files/phpmd_ruleset.xml'

-- phpstan
local function find_project_root()
    local path = vim.fn.expand('%:p:h') -- Get the directory of the current file
    while path ~= '/' do -- Stop when reaching the root directory
        if vim.fn.filereadable(path .. '/composer.json') == 1 then
            return path
        end
        path = vim.fn.fnamemodify(path, ':h') -- Move up one directory
    end
    return vim.fn.getcwd() -- If no composer.json found, return the current working directory
end

local function find_phpstan_neon(root_path)
    local phpstan_neon_path = root_path .. '/phpstan.neon'
    if vim.fn.filereadable(phpstan_neon_path) == 1 then
        return phpstan_neon_path
    else
        return os.getenv("HOME") .. '/.dotfiles/roles/neovim/files/phpstan_configuration.neon'
    end
end

local project_root = find_project_root()

vim.g.ale_php_phpstan_executable = os.getenv("HOME") .. '/.config/composer/vendor/bin/phpstan'
vim.g.ale_php_phpstan_configuration = find_phpstan_neon(project_root)
vim.g.ale_php_phpstan_autoload = project_root .. '/vendor/autoload.php'

-- mason

require('mason').setup({})
require'lspconfig'.phpactor.setup{}
require("mason-lspconfig").setup({
    ensure_installed = {"phpactor"},
})

function RunPhpactorRefactorCommand(transform_type)
  local current_file = vim.fn.shellescape(vim.fn.expand('%:p'))
  local command = string.format('phpactor class:transform %s --transform=%s', current_file, transform_type)
  
  local job_id = vim.fn.jobstart(command, {
    on_exit = function(_, code)
      if code == 0 then
        print('PHPactor command executed successfully')
        
        -- Reload the buffer to reflect changes
        vim.cmd('e')
      else
        print('PHPactor command failed with exit code:', code)
      end
    end
  })
end

-- xdebug
local dap = require('dap')

dap.adapters.php = {
  type = 'executable',
  command = 'node',
  args = { '/home/joey/vscode-php-debug/out/phpDebug.js' }
}

dap.configurations.php = {
  {
    type = 'php',
    request = 'launch',
    name = 'Listen for Xdebug',
    port = 9003,
	pathMappings = {
		["/app"] = "${workspaceFolder}/legacy",
	}
  }
}

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

function OpenDebugWidget()
  local widgets = require('dap.ui.widgets')
  widgets.centered_float(widgets.scopes)
end

function OpenDebugWidgetInWindow()
  local widgets = require('dap.ui.widgets')
  local my_sidebar = widgets.sidebar(widgets.scopes)
  my_sidebar.open()
end


-- snippets
local cmp = require('cmp')
local cmp_action = require('lsp-zero').cmp_action()
local cmp_format = require('lsp-zero').cmp_format()

require('luasnip.loaders.from_snipmate').lazy_load()

cmp.setup({
  sources = {
    {name = 'nvim_lsp'},
    {name = 'luasnip'},
  },
  mapping = cmp.mapping.preset.insert({
    ['<C-f>'] = cmp_action.luasnip_jump_forward(),
    ['<C-b>'] = cmp_action.luasnip_jump_backward(),
	['<CR>'] = cmp.mapping.confirm({select = true}),
  }),
  formatting = cmp_format
})

-- custom snippets
local ls = require("luasnip")
local snip = ls.snippet
local node = ls.snippet_node
local text = ls.text_node
local insert = ls.insert_node
local func = ls.function_node
local choice = ls.choice_node
local dynamicn = ls.dynamic_node

local keymap = vim.api.nvim_set_keymap
local opts = { noremap = true, silent = true }
keymap("i", "<c-j>", "<cmd>lua require'luasnip'.jump(1)<CR>", opts)
keymap("s", "<c-j>", "<cmd>lua require'luasnip'.jump(1)<CR>", opts)
keymap("i", "<c-k>", "<cmd>lua require'luasnip'.jump(-1)<CR>", opts)
keymap("s", "<c-k>", "<cmd>lua require'luasnip'.jump(-1)<CR>", opts)


local date = function() return {os.date('%Y-%m-%d')} end

ls.add_snippets(nil, {
    php = {
		snip({
			trig = "pubf",
			dscr = "Public function",
			priority=1000,
			regTrig=false,
		},
		{
			text({"public function ",}), insert(1, "name"), text({"(",}), insert(2, "params"), text({"): ",}), insert(3, "return type"), text({"",
			"{"}), text({"",
			""}), insert(0), text({"",
			""}), text({"}"})
		}
	  ),
    },
})

