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

-- imports
local previewers = require('telescope.previewers')

local tbuiltin = require('telescope.builtin')
local telescope = require('telescope')
local finders = require('telescope.finders')
local pickers = require('telescope.pickers')
local sorters = require('telescope.sorters')
local actions = require('telescope.actions')
local action_state = require('telescope.actions.state')
local conf = require('telescope.config').values

local Path = require('plenary.path')

-- projects


--- git
require('gitsigns').setup()

vim.g.gitblame_date_format = '%a %d-%m-%y'


-- loop through a to z
local set_keymap = vim.api.nvim_set_keymap
for i = 97, 122 do
	local letter_normal = string.char(i)
	local letter = string.upper(letter_normal)
  set_keymap("n", "<Leader>m" .. letter_normal, ":ma " .. letter .. "<CR>", { noremap = true, silent = true, desc = "Create mark for: " .. letter })
  set_keymap("n", "<Leader>fm" .. letter_normal, "`" .. letter, { noremap = true, silent = true, desc = "Go to mark for: " .. letter })
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


-- Function to get the git root directory
function get_git_root_or_nil()
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

function run_phpstan()
  vim.cmd(":below 10split | :terminal cd legacy && vendor/bin/phpstan analyze Core Common Component app src --memory-limit=-1 -c phpstan.neon.dist")
end

function run_csfix()
  vim.cmd(":below 10split | :terminal bin/cs.php fix")
end

function run_database_import()
	vim.ui.input({ prompt = 'Enter database name: ' }, function(input)
		vim.cmd("!bin/db i " .. input)
	end)
end

local function get_customers_list()
  local output = vim.fn.systemlist("bin/db customers | tail -n +2 | awk -F'|' '{print $2}' | sed 's/^ *//; s/ *$//' | grep -v '^$' | grep -v '^Name$'")
  return output
end

local function get_customer_databases_list()
  local output = vim.fn.systemlist("bin/db customers | tail -n +2 | awk -F'|' '{print $3}' | sed 's/^ *//; s/ *$//' | grep -v '^$' | grep -v '^Database$'")
  return output
end

local function get_customers_url_list()
  local output = vim.fn.systemlist("bin/db customers | tail -n +2 | awk -F'|' '{print $4}' | sed 's/^ *//; s/ *$//' | grep -v '^$' | grep -v '^Url$'")
  return output
end

function run_database_migration()
  local opts = {}
  local customers = get_customers_list()

  pickers.new(opts, {
    prompt_title = "Customers",
    finder = finders.new_table {
      results = customers
    },
    sorter = conf.generic_sorter(opts),
    attach_mappings = function(prompt_bufnr, map)
      actions.select_default:replace(function()
        actions.close(prompt_bufnr)
        local selection = action_state.get_selected_entry()
        local name = selection[1]
        vim.cmd('!bin/db m ' .. name)
      end)
      return true
    end,
  }):find()
end

function php_clear_cache()
	vim.cdm('cd legacy && bin/console cache:clear');
end

function run_database_delete()
  local opts = {}
  local customers = get_customer_databases_list()

  pickers.new(opts, {
    prompt_title = "Customers",
    finder = finders.new_table {
      results = customers
    },
    sorter = conf.generic_sorter(opts),
    attach_mappings = function(prompt_bufnr, map)
      actions.select_default:replace(function()
        actions.close(prompt_bufnr)
        local selection = action_state.get_selected_entry()
        local name = selection[1]
        vim.cmd('!bin/db db:drop ' .. name)
      end)
      return true
    end,
  }):find()
end

function run_database_customer_url()
  local opts = {}
  local customers = get_customers_list()

  pickers.new(opts, {
    prompt_title = "Customers",
    finder = finders.new_table {
      results = customers
    },
    sorter = conf.generic_sorter(opts),
    attach_mappings = function(prompt_bufnr, map)
      actions.select_default:replace(function()
        actions.close(prompt_bufnr)
        local selection = action_state.get_selected_entry()
        local name = selection[1]
				local url = "https://dyflexis.dev.wodanbrothers.com/" .. name;
				os.execute("xdg-open " .. url)

      end)
      return true
    end,
  }):find()
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
          command = find_test_command_from_current_file()
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

function find_test_command_from_current_file()
    -- Get the current file path
    local current_file = vim.fn.expand('%:p')
    local current_file_name = vim.fn.expand('%:t')

    -- Define the test groups to look for
    local test_groups = { 'unit', 'integration', 'api' }

    -- Function to find the test group in the path
    local function find_test_group(path, groups)
        for _, group in ipairs(groups) do
            if path:find(group) then
                return group
            end
        end
        return nil
    end

    -- Find the test group
    local test_group = find_test_group(current_file, test_groups)

    if not test_group then
        print('No test group found in the current path')
        return
    end

    -- Get the path from test group to the current file
    local test_path = current_file:match(test_group .. '/(.*)')

    if test_group == 'integration' or test_group == 'api' then
        if test_path and test_path:sub(1, 1) == '/' then
            test_path = test_path:sub(2)
        end
        return string.format('./test_runner.sh %s %s', test_group, test_path)
    elseif test_group == 'unit' then
        return string.format('./test_runner.sh unit --filter %s', current_file_name)
    end
end


-- fixers/formatters

--vim.g.ale_linters = {'cspell'}
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

-- rainbow brackets
local rainbow_delimiters = require 'rainbow-delimiters'

---@type rainbow_delimiters.config
vim.g.rainbow_delimiters = {
    strategy = {
        [''] = rainbow_delimiters.strategy['global'],
        vim = rainbow_delimiters.strategy['local'],
    },
    query = {
        [''] = 'rainbow-delimiters',
        lua = 'rainbow-blocks',
    },
    priority = {
        [''] = 110,
        lua = 210,
    },
    highlight = {
        'RainbowDelimiterRed',
        'RainbowDelimiterYellow',
        'RainbowDelimiterBlue',
        'RainbowDelimiterOrange',
        'RainbowDelimiterGreen',
        'RainbowDelimiterViolet',
        'RainbowDelimiterCyan',
    },
}

-- indent blank line
local highlight = {
    "RainbowRed",
    "RainbowYellow",
    "RainbowBlue",
    "RainbowOrange",
    "RainbowGreen",
    "RainbowViolet",
    "RainbowCyan",
}
local hooks = require "ibl.hooks"
-- create the highlight groups in the highlight setup hook, so they are reset
-- every time the colorscheme changes
hooks.register(hooks.type.HIGHLIGHT_SETUP, function()
    vim.api.nvim_set_hl(0, "RainbowRed", { fg = "#E06C75" })
    vim.api.nvim_set_hl(0, "RainbowYellow", { fg = "#E5C07B" })
    vim.api.nvim_set_hl(0, "RainbowBlue", { fg = "#61AFEF" })
    vim.api.nvim_set_hl(0, "RainbowOrange", { fg = "#D19A66" })
    vim.api.nvim_set_hl(0, "RainbowGreen", { fg = "#98C379" })
    vim.api.nvim_set_hl(0, "RainbowViolet", { fg = "#C678DD" })
    vim.api.nvim_set_hl(0, "RainbowCyan", { fg = "#56B6C2" })
end)

vim.g.rainbow_delimiters = { highlight = highlight }
require("ibl").setup { scope = { highlight = highlight } }

hooks.register(hooks.type.SCOPE_HIGHLIGHT, hooks.builtin.scope_highlight_from_extmark)

-- Tabnine

require('tabnine').setup({
  disable_auto_comment=true,
  accept_keymap="<Tab>",
  dismiss_keymap = "<C-]>",
  debounce_ms = 800,
  suggestion_color = {gui = "#808080", cterm = 244},
  exclude_filetypes = {"TelescopePrompt", "NvimTree"},
  log_file_path = nil, -- absolute path to Tabnine log file
  ignore_certificate_errors = false,
})

-- dashboard

function delete_session()
  local sessions_dir = vim.fn.expand('~/.local/share/nvim/neovim-sessions/')

  local session_files = vim.fn.globpath(sessions_dir, '*', false, true)

  pickers.new({}, {
    prompt_title = 'Neovim Sessions',
    finder = finders.new_table({
      results = session_files,
    }),
    sorter = conf.generic_sorter({}),
    previewer = previewers.cat.new({}),
    attach_mappings = function(prompt_bufnr, map)
      map('i', '<CR>', function()
        local selection = action_state.get_selected_entry()
        actions.close(prompt_bufnr)

        vim.fn.system({'rm', '-rf', selection[1]})
      end)
      return true
    end,
  }):find()
end

-- key-binds
local wk = require("which-key")

wk.register(
	{

		["<leader>"] = {

			q = {':Neotree close<cr>:cclose<CR>', 'Close all other tabs'},
			v = {
				name = "Version",
				i = {':e ~/.dotfiles/roles/neovim/files/nvim/init.lua<cr>', 'Open init.lua'},
				s = {':source ~/.dotfiles/roles/neovim/files/nvim/init.lua<cr>', 'Reload init.lua'},
			},

			e = {
				name = "Error",
				f = {'<cmd>lua require("trouble").toggle("diagnostics")<cr><cmd>lua require("trouble").focus("diagnostics")<cr>', 'Open error window'},
			},

			f = {
				name = "Find",
				f = {
					name = "File",
					n = {tbuiltin.find_files, 'Name'},
					i = {tbuiltin.live_grep, 'In files'},
					s = {tbuiltin.grep_string, 'Selected String'},
					o = {tbuiltin.buffers, 'Open files'},
				},
				g = {
					name = "Grep",
					r = {'<cmd>lua require("spectre").toggle()<CR>', 'Replace'},
					w = {'<cmd>lua require("spectre").open_visual({select_word=true})<CR>', 'Word under cursor'},
				},
				m = {
					name = "mark",
				},
				c = {tbuiltin.registers, 'Clipboard'},
				s = {':TagbarOpenAutoClose<cr>', 'Symbols'},
				d = {':TodoTelescope keywords=DOING,HACK<cr>', 'Todos'},
			},

			s = {
				name = "Symbol",
				c = {tbuiltin.spell_suggest, 'Check'},
			},

			h = {':WhichKey<cr>', 'Help'},

			p = {
				name = "Project",
				l = {':Telescope neovim-project discover<cr>', 'List'},
				f = {':Neotree toggle left<cr>', 'Files'},
				F = {':Neotree toggle float<cr>', 'Floating files'},
				c = {
					name = "Current",
					f = {':Neotree reveal left<cr>', 'Files'},
					F = {':Neotree reveal float<cr>', 'Floating files'},
				},
				o = {
					name = "Open",
					f = {':Neotree buffers left<cr>', 'Files'},
					F = {':Neotree buffers float<cr>', 'Floating files'},
				},
			},

			g = {
				name = "Git",
				s = {':terminal lazygit<cr>:startinsert<cr>', 'Status'},
				b = {':GitBlameToggle<cr>', 'Blame'},
				d = {':Gitsigns preview_hunk<cr>', 'Diff'},
			},

			v = {
				name = "View",
				m = {':MarkdownPreview<cr>', 'Markdown'},
				M = {':MarkdownPreviewStop<cr>', 'Close markdown'},
			},

			M = {':Telescope marks<cr>', 'Show all marks'},

			m = {
				name = "Mark",
				C = {':delmarks a-z<cr>', 'Delete all'},
			},

			n = {'<Plug>(miniyank-cycle)', 'Miniyank: next'},
			N = {'<Plug>(miniyank-cycleback)', 'Miniyank: prev'},

			t = {
				name = "Task",
				t = {
					name = "Test",
					t = {':lua search_and_display_groups("")<CR>', 'All'},
					f = {':lua search_and_display_groups("--fail-fast")<CR>', 'Fail fast'},
					r = {':lua search_and_display_groups("--no-rebuild")<CR>', 'No rebuild'},
					a = {':lua search_and_display_groups("--fail-fast --no-rebuild")<CR>', 'Fail fast & No rebuild'},
				},
				d = {
					name = "Database",
					i = {':lua run_database_import()<CR>', 'Import'},
					m = {':lua run_database_migration()<CR>', 'Migrate'},
					d = {':lua run_database_delete()<CR>', 'Delete'},
					o = {':lua run_database_customer_url()<CR>', 'Open'},
				},
				p = {
					name = "PHP",
					c = {':lua php_clear_cache()<CR>', 'Clear Cache'},
				},
				p = {':lua run_phpstan()<CR>', 'phpstan'},
				c = {':lua run_csfix()<CR>', 'cs-fix'},
			}

		},

		['<A-q>'] = {':bprev<CR>', 'Go to prev tab'},
		['<A-e>'] = {':bnext<CR>', 'Go to next tab'},

		['p'] = {'<Plug>(miniyank-autoput)', 'Paste'},
		['P'] = {'<Plug>(miniyank-autoPut)', 'Paste before'},

		['<A-w>'] = {':Bdelete<CR>', 'Close tab'},
		['<A-W>'] = {':Bdelete!<CR>', 'Force close tab'},
		['<C-A-w>'] = {':bufdo bd<CR>:Bdelete<CR>', 'Close all tab'},
	}
)

wk.register(
	{
		['<C-M-c>'] = {'"+y', "Copy to clipboard"},
		["<leader>"] = {

			f = {
				name = "Find",
				f = {
					name = "File",
					s = {tbuiltin.grep_string, 'Selected String'},
				},
			},
		},
	},
	{
		mode = "v"
	}
)

