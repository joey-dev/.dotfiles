local vim = vim
local execute = vim.api.nvim_command
local fn = vim.fn


vim.g.mapleader = " "

vim.cmd("language en_US.utf8")
vim.api.nvim_set_keymap("", "<Space>", "<Nop>", { noremap = true })

local lazypath = vim.fn.stdpath("data") .. "/lazy/lazy.nvim"
if not vim.loop.fs_stat(lazypath) then
  vim.fn.system({
    "git",
    "clone",
    "--filter=blob:none",
    "https://github.com/folke/lazy.nvim.git",
    "--branch=stable", -- latest stable release
    lazypath,
  })
end
vim.opt.rtp:prepend(lazypath)

require("lazy").setup("plugins")

vim.api.nvim_set_keymap("n", "<leader>vi", ":e ~/.dotfiles/roles/neovim/files/nvim/init.lua<cr>", { noremap = true })
vim.api.nvim_set_keymap("n", "<leader>vs", ":source ~/.dotfiles/roles/neovim/files/nvim/init.lua<cr>", { noremap = true })
-- copy to clipboard
vim.api.nvim_set_keymap('v', '<C-M-c>', '"+y', { noremap = true, silent = true })

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

-- colors
vim.fn.matchadd("GreenBang", "!")

require("catppuccin").setup({
    flavour = "mocha", -- latte, frappe, macchiato, mocha
    background = {
        light = "latte",
        dark = "mocha",
    },
    transparent_background = false,
    show_end_of_buffer = false,
    term_colors = false,
    dim_inactive = {
        enabled = false,
        shade = "dark",
        percentage = 0.15,
    },
    no_italic = false,
    no_bold = false,
    no_underline = false,
    styles = {
        comments = { "italic" },
        conditionals = { "italic" },
        loops = {},
        functions = {},
        keywords = {},
        strings = {},
        variables = {},
        numbers = {},
        booleans = {},
        properties = {},
        types = {},
        operators = {},
    },
	color_overrides = {
		mocha = {
			base = "#000000",
			mantle = "#000000",
			crust = "#000000",
		},
	},
	custom_highlights = function(colors)
        return {
            GreenBang = { fg = "lightgreen", bg = "darkgreen" },
        }
    end,
	highlight_overrides = {},
    integrations = {
        cmp = true,
        gitsigns = true,
        nvimtree = true,
        treesitter = true,
		harpoon = true,
		dap = true,
		dap_ui = true,
        notify = false,
        mini = {
            enabled = true,
            indentscope_color = "",
        },
    },
})

vim.cmd.colorscheme "catppuccin-mocha"

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
vim.keymap.set('n', '<Leader>gb', ':GitBlameToggle<cr>')
vim.keymap.set('n', '<Leader>go', ':GitBlameOpenCommitURL<cr>')
vim.g.gitblame_date_format = '%a %d-%m-%y'

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

-- minyank
vim.api.nvim_set_keymap('n', 'p', '<Plug>(miniyank-autoput)', { noremap = false })
vim.api.nvim_set_keymap('n', 'P', '<Plug>(miniyank-autoPut)', { noremap = false })
vim.api.nvim_set_keymap('n', '<leader>n', '<Plug>(miniyank-cycle)', { noremap = false })
vim.api.nvim_set_keymap('n', '<leader>N', '<Plug>(miniyank-cycleback)', { noremap = false })

-- bbye
vim.api.nvim_set_keymap('n', '<M-w>', ':Bdelete<cr>', { noremap = false })

-- tagbar
vim.api.nvim_set_keymap('n', '<leader>fs', ':TagbarOpenAutoClose<cr>', { noremap = false })

vim.api.nvim_set_keymap('n', '<leader>ft', ':TodoTelescope keywords=DOING,HACK<cr>', { noremap = false })

-- snippets
local cmp = require('cmp')
local cmp_action = require('lsp-zero').cmp_action()
local cmp_format = require('lsp-zero').cmp_format()
local luasnip = require("luasnip")

require('luasnip.loaders.from_snipmate').lazy_load()

cmp.setup({
  sources = {
    {name = 'nvim_lsp'},
    {name = 'luasnip'},
  },
  mapping = cmp.mapping.preset.insert({
		['<CR>'] = cmp.mapping(function(fallback)
			if cmp.visible() then
        if luasnip.expandable() then
          luasnip.expand()
        else
          cmp.confirm({
						select = true,
					})
        end
      else
				fallback()
      end
    end),

    ["<Tab>"] = cmp.mapping(function(fallback)
      if luasnip.locally_jumpable(1) then
        luasnip.jump(1)
      else
        fallback()
      end
    end, { "i", "s" }),

    ["<S-Tab>"] = cmp.mapping(function(fallback)
      if luasnip.locally_jumpable(-1) then
        luasnip.jump(-1)
      else
        fallback()
      end
    end, { "i", "s" }),
  }),
  formatting = cmp_format
})
