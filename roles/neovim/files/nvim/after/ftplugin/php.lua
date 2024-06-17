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

require'dapui'.setup(
	{
    controls = {
      element = "repl",
      enabled = true,
      icons = {
        disconnect = "",
        pause = "",
        play = "",
        run_last = "",
        step_back = "",
        step_into = "",
        step_out = "",
        step_over = "",
        terminate = ""
      }
    },
    element_mappings = {},
    expand_lines = true,
    floating = {
      border = "single",
      mappings = {
        close = { "q", "<Esc>" }
      }
    },
    force_buffers = true,
    icons = {
      collapsed = "",
      current_frame = "",
      expanded = ""
    },
    layouts = {
			{
				elements = {
					{
						id = "stacks",
						size = 0.25
					},
					{
						id = "scopes",
						size = 0.5
					},
					{
						id = "breakpoints",
						size = 0.25
					},
				},
				position = "left",
				size = 40
			},
			{
				elements = {
					{
						id = "watches",
						size = 1.0
					},
				},
				position = "bottom",
				size = 10
			}
		},
    mappings = {
      edit = "e",
      expand = { "<CR>", "<2-LeftMouse>" },
      open = "o",
      remove = "d",
      repl = "r",
      toggle = "t"
    },
    render = {
      indent = 1,
      max_value_lines = 100
    }
  }
)

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
vim.api.nvim_set_keymap('n', '<A-u>', ":lua require'dapui'.toggle()<CR>", { noremap = true, silent = true, nowait = false })

function OpenDebugWidget()
  local widgets = require('dap.ui.widgets')
  widgets.centered_float(widgets.scopes)
end

function OpenDebugWidgetInWindow()
  local widgets = require('dap.ui.widgets')
  local my_sidebar = widgets.sidebar(widgets.scopes)
  my_sidebar.open()
end

-- Switch between test file
function switch_between_file_and_test(test_type)
    local current_file_path = vim.fn.expand("%:p")
    local is_test_file = string.find(current_file_path, "/tests/" .. test_type .. "/") ~= nil

    if is_test_file then
        local source_file_path = string.gsub(current_file_path, "/tests/" .. test_type .. "/", "/")
        source_file_path = string.gsub(source_file_path, "Test%.php$", ".php")

        vim.cmd("edit " .. source_file_path)
    else
        local test_file_path = string.gsub(current_file_path, "Component", "tests/" .. test_type .. "/Component")
        test_file_path = string.gsub(test_file_path, "%.php$", "Test.php")

        vim.cmd("edit " .. test_file_path)
    end
end

vim.api.nvim_set_keymap('n', '<leader>fut', '<cmd>lua switch_between_file_and_test("unit")<CR>', { noremap = true, silent = true })
vim.api.nvim_set_keymap('n', '<leader>fit', '<cmd>lua switch_between_file_and_test("integration")<CR>', { noremap = true, silent = true })
vim.api.nvim_set_keymap('n', '<leader>fat', '<cmd>lua switch_between_file_and_test("api")<CR>', { noremap = true, silent = true })

