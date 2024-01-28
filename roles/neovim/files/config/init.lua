local vim = vim
local execute = vim.api.nvim_command
local fn = vim.fn


vim.g.mapleader = " "

vim.cmd("language en_US.utf8")
vim.api.nvim_set_keymap("", "<Space>", "<Nop>", { noremap = true })

require("plugins")

vim.api.nvim_set_keymap("n", "<leader>vi", ":e ~/.dotfiles/roles/neovim/files/config/init.lua<cr>", { noremap = true })
vim.api.nvim_set_keymap("n", "<leader>vs", ":source ~/.dotfiles/roles/neovim/files/config/init.lua<cr>", { noremap = true })
-- copy to clipboard
vim.api.nvim_set_keymap('v', '<M-c>', '"+y', { noremap = true, silent = true })

-- nvim settings
vim.o.completeopt = "menuone,noinsert,noselect"
vim.o.number = true
vim.o.tabstop = 4
vim.o.softtabstop = 4
vim.o.shiftwidth = 4
vim.o.smartindent = true
vim.o.hlsearch = true
vim.o.ignorecase = true
vim.o.showmode = true
vim.o.relativenumber = true
vim.o.undolevels = 1000
vim.o.so = 100

-- plugin start
local harpoon = require("harpoon")
harpoon:setup()

-- global keymap
vim.keymap.set('n', '<Leader>t', ':FloatermNew<cr>')
-- projects
vim.keymap.set('n', '<Leader>pl', ':ProjectList<cr>')

local tbuiltin = require('telescope.builtin')
vim.keymap.set('n', '<leader>ff', tbuiltin.find_files, {})
vim.keymap.set('n', '<leader>fif', tbuiltin.live_grep, {})

-- task manager
vim.keymap.set('n', '<Leader>tm', ':ProjectRun<cr>')

-- tree
vim.keymap.set('n', '<Leader>pf', ':Neotree<cr>')
vim.keymap.set('n', '<Leader>pcf', ':Neotree reveal<cr>')
vim.keymap.set('n', '<Leader>pof', ':Neotree buffers<cr>')

--- git
vim.keymap.set('n', '<Leader>gs', ':FloatermNew lazygit<cr>')

-- view
vim.keymap.set('n', '<Leader>vm', ':MarkdownPreview<cr>')
vim.keymap.set('n', '<Leader>vM', ':MarkdownPreviewStop<cr>')

-- buffer
vim.keymap.set("n", "<A-q>", ':bprev<cr>')
vim.keymap.set("n", "<A-e>", ':bnext<cr>')

-- harpoon
function get_git_root()
    local git_root = vim.fn.systemlist('git rev-parse --show-toplevel')[1]
    return git_root
end

function remove_current_file_from_harpoon()
    local current_file = vim.fn.expand('%:p') -- Get the full path of the current file
    local git_root = get_git_root()

    if git_root ~= '' and current_file:match(git_root) then
        local relative_path = current_file:sub(#git_root + 2) -- +2 to remove the leading '/'

		local names = harpoon:list():display()
		for i, name in ipairs(names) do
			if name == relative_path then
				print (i)
				harpoon:list():removeAt(i)
				break
			end
		end
    else
        print("Not in a Git project or unable to determine Git root.")
    end
end

vim.keymap.set("n", "<leader>mf", function() harpoon:list():append() end)
vim.keymap.set("n", "<leader>mc", function() harpoon:list():clear() end)
vim.keymap.set("n", "<leader>mr", remove_current_file_from_harpoon)
vim.keymap.set("n", "<leader>M", function() harpoon.ui:toggle_quick_menu(harpoon:list()) end)
vim.keymap.set("n", "<leader>mq", function() harpoon:list():prev() end)
vim.keymap.set("n", "<leader>me", function() harpoon:list():next() end)

require('lualine').setup {
  options = {
    icons_enabled = true,
    theme = 'auto',
    component_separators = { left = '', right = ''},
    section_separators = { left = '', right = ''},
    disabled_filetypes = {
      statusline = {},
      winbar = {},
    },
    ignore_focus = {},
    always_divide_middle = true,
    globalstatus = false,
    refresh = {
      statusline = 1000,
      tabline = 1000,
      winbar = 1000,
    }
  },
  sections = {
    lualine_a = {'mode'},
    lualine_b = { {'filename', path=1} },
    lualine_c = {},
    lualine_x = {'location'},
    lualine_y = {'filetype'},
    lualine_z = {'branch', 'diff', 'diagnostics'},
  },
  inactive_sections = {
    lualine_a = {},
    lualine_b = {},
    lualine_c = {'filename'},
    lualine_x = {'location'},
    lualine_y = {},
    lualine_z = {}
  },
  tabline = {},
  winbar = {},
  inactive_winbar = {},
  extensions = {}
}

-- php
vim.api.nvim_set_keymap('n', '<leader>rn', ':lua RunPhpactorRefactorCommand("fix_namespace_class_name")<CR>', { noremap = true, silent = true, nowait = false }) -- needs testing
vim.api.nvim_set_keymap('n', '<leader>gf', ':lua RunPhpactorRefactorCommand("complete_constructor")<CR>', { noremap = true, silent = true, nowait = false })
vim.api.nvim_set_keymap('n', '<leader>gm', ':lua RunPhpactorRefactorCommand("implement_contracts")<CR>', { noremap = true, silent = true, nowait = false }) -- needs testing
vim.api.nvim_set_keymap('n', '<leader>rm', ":lua require('phpactor').rpc('context_menu', {})<CR>", { noremap = true, silent = true, nowait = false })
vim.api.nvim_set_keymap('v', '<leader>rm', ":lua require('phpactor').rpc('context_menu', {})<CR>", { noremap = true, silent = true, nowait = false })
vim.api.nvim_set_keymap('n', '<leader>gi', ":lua require('phpactor').rpc('import_missing_classes', {})<CR>", { noremap = true, silent = true, nowait = false })
vim.api.nvim_set_keymap('n', '<leader>gc', ":lua require('phpactor').rpc('copy_class', {})<CR>", { noremap = true, silent = true, nowait = false })
vim.api.nvim_set_keymap('n', '<leader>gn', ":lua require('phpactor').rpc('new_class', {})<CR>", { noremap = true, silent = true, nowait = false })
vim.api.nvim_set_keymap('n', '<leader>rc', ":lua require('phpactor').rpc('move_class', {})<CR>", { noremap = true, silent = true, nowait = false })

vim.api.nvim_set_keymap('n', '<A-b>', ":lua require'dap'.toggle_breakpoint()<CR>", { noremap = true, silent = true, nowait = false })
vim.api.nvim_set_keymap('n', '<A-c>', ":lua require'dap'.continue()<CR>", { noremap = true, silent = true, nowait = false })
vim.api.nvim_set_keymap('n', '<A-o>', ":lua require'dap'.step_over()<CR>", { noremap = true, silent = true, nowait = false })
vim.api.nvim_set_keymap('n', '<A-i>', ":lua require'dap'.step_into()<CR>", { noremap = true, silent = true, nowait = false })
vim.api.nvim_set_keymap('n', '<A-l>', ":lua require'dap'.repl.open()<CR>", { noremap = true, silent = true, nowait = false })

-- wanted:
-- PhpactorExtractExpression
-- PhpactorExtractMethod

local lsp = require("lsp-zero")

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

require('mason').setup({})
require'lspconfig'.phpactor.setup{}
require("mason-lspconfig").setup({
    ensure_installed = {"phpactor"},
})

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
  --- (Optional) Show source name in completion menu
  formatting = cmp_format
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

local dap = require('dap')

dap.adapters.php = {
  type = 'executable',
  command = 'node',
  args = { '~/vscode-php-debug/out/phpDebug.js' }
}

dap.configurations.php = {
  {
    type = 'php',
    request = 'launch',
    name = 'Listen for Xdebug',
    port = 9000
  }
}

