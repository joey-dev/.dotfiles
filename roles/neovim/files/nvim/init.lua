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

-- projects
vim.keymap.set('n', '<Leader>pl', ':Telescope neovim-project discover<cr>')

local tbuiltin = require('telescope.builtin')
vim.keymap.set('n', '<leader>ff', tbuiltin.find_files, {})
vim.keymap.set('n', '<leader>fif', tbuiltin.live_grep, {})

-- tree
vim.keymap.set('n', '<Leader>pf', ':Neotree toggle left<cr>')
vim.keymap.set('n', '<Leader>pF', ':Neotree toggle float<cr>')
vim.keymap.set('n', '<Leader>pcf', ':Neotree reveal left<cr>')
vim.keymap.set('n', '<Leader>pcF', ':Neotree reveal float<cr>')
vim.keymap.set('n', '<Leader>pof', ':Neotree buffers left<cr>')
vim.keymap.set('n', '<Leader>poF', ':Neotree buffers float<cr>')

--- git
require('gitsigns').setup()

vim.keymap.set('n', '<Leader>gs', ':FloatermNew --height=1.0 --width=1.0 lazygit<cr>')
vim.keymap.set('n', '<Leader>gb', ':GitBlameToggle<cr>')
vim.keymap.set('n', '<Leader>gd', ":Gitsigns preview_hunk<cr>")
vim.g.gitblame_date_format = '%a %d-%m-%y'

-- view
vim.keymap.set('n', '<Leader>vm', ':MarkdownPreview<cr>')
vim.keymap.set('n', '<Leader>vM', ':MarkdownPreviewStop<cr>')

-- buffer
vim.keymap.set("n", "<A-q>", ':bprev<cr>')
vim.keymap.set("n", "<A-e>", ':bnext<cr>')

-- marks
vim.keymap.set("n", "<Leader>M", ':Telescope marks<cr>')
vim.keymap.set("n", "<Leader>mC", ':delmarks a-z<cr>')

-- loop through a to z
local set_keymap = vim.api.nvim_set_keymap
for i = 97, 122 do
	local letter = string.char(i)
    set_keymap("n", "<Leader>m" .. letter, ":ma " .. letter .. "<CR>", { noremap = true, silent = true })
end

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
    lualine_c = {
			function()
				return require('lsp-progress').progress()
			end,
		},
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


-- LSP progress bar

vim.api.nvim_create_augroup("lualine_augroup", { clear = true })
vim.api.nvim_create_autocmd("User", {
  group = "lualine_augroup",
  pattern = "LspProgressStatusUpdated",
  callback = require("lualine").refresh,
})

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

-- run tests in directory

local telescope = require('telescope')
local finders = require('telescope.finders')
local pickers = require('telescope.pickers')
local sorters = require('telescope.sorters')
local actions = require('telescope.actions')
local action_state = require('telescope.actions.state')
local Path = require('plenary.path')

-- Function to get the git root directory
local function get_git_root_or_nil()
  local git_root = vim.fn.systemlist("git rev-parse --show-toplevel")[1]
  if git_root == "" then
    return nil
  end
  return git_root
end

local test_groups = {"unit", "integration", "api"}

-- Function to recursively search files in a directory
local function search_files(dir)
  local results = {}
  if Path:new(dir):is_dir() then
    local p = io.popen('find "'..dir..'" -type f')
    for file in p:lines() do
      table.insert(results, file)
    end
    p:close()
  end
  return results
end

-- Function to extract @group tags from a file
local function extract_groups(file)
  local groups = {}
  for line in io.lines(file) do
    local group = line:match("@group%s+(%w+)")
    if group then
      groups[group] = true
    end
  end
  return groups
end

function search_and_display_groups(post_fix)
  local git_root = get_git_root_or_nil()
  if not git_root then
    vim.api.nvim_err_writeln("Error: Not a git repository or unable to find git root.")
    return
  end

  local results = {}

  -- Add predefined options
  table.insert(results, "current file")
  table.insert(results, "all unit")
  table.insert(results, "all integration")
  table.insert(results, "all api")

  for _, group in ipairs(test_groups) do
    local path = git_root .. "/legacy/tests/" .. group
    local files = search_files(path)
    local group_results = {}

    for _, file in ipairs(files) do
      local groups = extract_groups(file)
      for word in pairs(groups) do
        group_results[word] = true
      end
    end

    for word in pairs(group_results) do
      table.insert(results, group .. " " .. word)
    end
  end

  if vim.tbl_isempty(results) then
    vim.api.nvim_err_writeln("Warning: No test groups found. Showing predefined commands.")
  end

  pickers.new({}, {
    prompt_title = "Select Test Group",
    finder = finders.new_table {
      results = results
    },
    sorter = sorters.get_generic_fuzzy_sorter(),
    attach_mappings = function(prompt_bufnr, map)
      map('i', '<CR>', function()
        local selection = action_state.get_selected_entry()
        actions.close(prompt_bufnr)
        local selected = selection[1]
        local test_group, word = selected:match("^(%S+) (%S+)$")

        -- Determine the command to run based on the selection
        local command
        if selected == "current file" then
          command = "./test_runner.sh"
        elseif selected == "all unit" then
          command = "./test_runner.sh unit"
        elseif selected == "all integration" then
          command = "./test_runner.sh integration"
        elseif selected == "all api" then
          command = "./test_runner.sh api"
        else
          command = string.format("./test_runner.sh debug %s --group %s", test_group, word)
        end


				local formatted_post_fix
				if test_group == "unit" then
					formatted_post_fix = post_fix:gsub("%s*%-%-no%-rebuild%s*", "")
				else
					formatted_post_fix = post_fix
				end

        vim.cmd(string.format(":below 10split | :terminal %s %s", command, formatted_post_fix))
      end)
      return true
    end,
  }):find()
end

vim.keymap.set('n', '<Leader>tt',':lua search_and_display_groups("")<CR>', { noremap = true, silent = true })
vim.keymap.set('n', '<Leader>tf',':lua search_and_display_groups("--fail-fast")<CR>', { noremap = true, silent = true })
vim.keymap.set('n', '<Leader>tr',':lua search_and_display_groups("--no-rebuild")<CR>', { noremap = true, silent = true })
vim.keymap.set('n', '<Leader>ta',':lua search_and_display_groups("--fail-fast --no-rebuild")<CR>', { noremap = true, silent = true })


-- fixers/formatters

vim.g.ale_fixers = {'trim_whitespace', 'remove_trailing_lines'}

vim.g.ale_fix_on_save = 1

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

-- spectre
vim.api.nvim_set_keymap("n", "<leader>fr", '<cmd>lua require("spectre").toggle()<CR>', { noremap = true })
vim.api.nvim_set_keymap("n", "<leader>fw", '<cmd>lua require("spectre").open_visual({select_word=true})<CR>', { noremap = true })

vim.opt.termguicolors = true
require("bufferline").setup{
	options = {
		diagnostics = "nvim_lsp",
		diagnostics_update_in_insert = false,
		diagnostics_indicator = function(count, level, diagnostics_dict, context)
			local s = " "
			for e, n in pairs(diagnostics_dict) do
				local sym = e == "error" and " "
					or (e == "warning" and " " or "" )
				s = s .. n .. sym
			end
			return s
		end
	}
}
