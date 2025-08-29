return {

	{
		"coffebar/neovim-project",
		opts = {
			projects = {
				"~/Code/Work/*",
				"~/Code/Learning/*",
				"~/Code/Projects/*",
				"~/.dotfiles",
				"~/notes",
			},
			dashboard_mode = true,
		},
		init = function()
			-- enable saving the state of plugins in the session
			vim.opt.sessionoptions:append("globals") -- save global variables that start with an uppercase letter and contain at least one lowercase letter.
		end,
		dependencies = {
			{ "nvim-lua/plenary.nvim" },
			{ "nvim-telescope/telescope.nvim", tag = "0.1.4" },
			{ "Shatur/neovim-session-manager" },
		},
		lazy = false,
		priority = 100,
	},
	{
		'nvimdev/dashboard-nvim',
		event = 'VimEnter',
		config = function()
			require('dashboard').setup {
				theme = 'doom',
				config = {
					week_header = {
						enable = true,
					},
					center = {
						{
							icon = ' ',
							icon_hl = 'Title',
							desc = 'Find Project           ',
							desc_hl = 'String',
							key = 'b',
							keymap = '<leader>pl',
							key_hl = 'Number',
							key_format = ' %s', -- remove default surrounding `[]`
							action = 'Telescope neovim-project discover'
						},
						{
							icon = ' ',
							desc = 'Find Dotfiles',
							key = 'f',
							keymap = 'SPC f d',
							key_format = ' %s', -- remove default surrounding `[]`
							action = 'NeovimProjectLoad ~/.dotfiles'
						},
						{
							icon = ' ',
							desc = 'Find Notes',
							key = 'n',
							keymap = 'SPC f d',
							key_format = ' %s', -- remove default surrounding `[]`
							action = 'NeovimProjectLoad ~/notes'
						},
						{
							icon = ' ',
							desc = 'Remove session',
							key = 'r',
							keymap = 'SPC f d',
							key_format = ' %s', -- remove default surrounding `[]`
							action = 'lua delete_session()'
						},
					},
					footer = {}  --your footer
				}
			}
		end,
		dependencies = { {'nvim-tree/nvim-web-devicons'}}
	},

	{
		"HiPhish/rainbow-delimiters.nvim",
		dependencies = { { 'nvim-treesitter/nvim-treesitter'}},
		config = function()
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
		end
	},
	{
    "nvim-treesitter/nvim-treesitter",
    -- The build step is still correct
    build = ":TSUpdate",
    config = function()
        require("nvim-treesitter.configs").setup {
            -- `ensure_installed` is now a top-level key in the setup table.
            -- It ensures these parsers are installed on first run.
            ensure_installed = { "php", "javascript", "vue", "lua", "sql", "css", "scss" },

            -- This is a new, recommended option that automatically installs new
            -- parsers when you open a file that needs one.
            auto_install = true,

            -- The 'highlight' module configuration remains inside its own table.
            highlight = {
                enable = true,
                additional_vim_regex_highlighting = true,
            },

            -- It's also good practice to enable the indent module.
            indent = { enable = true },
        }
    end
	},
	{
		"nvim-neo-tree/neo-tree.nvim",
		branch = "v3.x",
		dependencies = {
		  "nvim-lua/plenary.nvim",
		  "nvim-tree/nvim-web-devicons",
		  "MunifTanjim/nui.nvim",
		  "3rd/image.nvim"
		},
		config = function()
			require("neo-tree").setup({
			  window = {
				position = "left",
				width = 40,
			  },
			})
		end,
	},
	{
		"folke/trouble.nvim"
	},

	{
		"lukas-reineke/indent-blankline.nvim", main = "ibl", opts = {},
		config = function()
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
		end,
	},

	{
		"folke/which-key.nvim",
		event = "VeryLazy",
		init = function()
			vim.o.timeout = true
			vim.o.timeoutlen = 500
		end,
		opts = {
			plugins = {
				presets = {
					operators = false,
					motions = false,
					text_objects = false,
					nav = false,
					z = false,
					g = false
				}
			}
		},
		dependencies = {
			"echasnovski/mini.nvim",
			"nvim-tree/nvim-web-devicons",
		},
		config = function(_, opts)
      -- KEYMAPS
      local wk = require("which-key")
      local utils = require("utils") -- Require your new utils file
			local tbuiltin = require('telescope.builtin')

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
								t = {':lua utils.search_and_display_groups("")<CR>', 'All'},
								f = {':lua utils.search_and_display_groups("--fail-fast")<CR>', 'Fail fast'},
								r = {':lua utils.search_and_display_groups("--no-rebuild")<CR>', 'No rebuild'},
								a = {':lua utils.search_and_display_groups("--fail-fast --no-rebuild")<CR>', 'Fail fast & No rebuild'},
							},
							d = {
								name = "Database",
								i = {':lua utils.run_database_import()<CR>', 'Import'},
								m = {':lua utils.run_database_migration()<CR>', 'Migrate'},
								d = {':lua utils.run_database_delete()<CR>', 'Delete'},
								o = {':lua utils.run_database_customer_url()<CR>', 'Open'},
								n = {':lua utils.create_new_migration()<CR>', 'Create new migration'},
							},
							P = {
								name = "PHP",
								c = {':lua utils.php_clear_cache()<CR>', 'Clear Cache'},
							},
							p = {':lua utils.run_phpstan()<CR>', 'phpstan'},
							c = {
								name = "cs-fix",
								c = {':lua utils.run_csfix("current")<CR>', 'current changes'},
								a = {':lua utils.run_csfix("master")<CR>', 'all changes'},
							}
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

			local set_keymap = vim.api.nvim_set_keymap
			for i = 97, 122 do
				local letter_normal = string.char(i)
				local letter = string.upper(letter_normal)
				set_keymap("n", "<Leader>m" .. letter_normal, ":ma " .. letter .. "<CR>", { noremap = true, silent = true, desc = "Create mark for: " .. letter })
				set_keymap("n", "<Leader>fm" .. letter_normal, "`" .. letter, { noremap = true, silent = true, desc = "Go to mark for: " .. letter })
			end
		end,
	},
	{
		"okuuva/auto-save.nvim",
		cmd = "ASToggle", -- optional for lazy loading on command
		event = { "InsertLeave", "TextChanged" }, -- optional for lazy loading on trigger events
		opts = {
				enabled = true, -- start auto-save when the plugin is loaded (i.e. when your package manager loads it)
				execution_message = {
					enabled = true,
					message = function() -- message to print on save
						return ("AutoSave: saved at " .. vim.fn.strftime("%H:%M:%S"))
					end,
					dim = 0.18, -- dim the color of `message`
					cleaning_interval = 1250, -- (milliseconds) automatically clean MsgArea after displaying `message`. See :h MsgArea
				},
				trigger_events = { -- See :h events
					immediate_save = { "BufLeave", "FocusLost", "CursorHold" }, -- vim events that trigger an immediate save
					defer_save = {}, -- vim events that trigger a deferred save (saves after `debounce_delay`)
					cancel_defered_save = {}, -- vim events that cancel a pending deferred save
				},
				-- function that takes the buffer handle and determines whether to save the current buffer or not
				-- return true: if buffer is ok to be saved
				-- return false: if it's not ok to be saved
				-- if set to `nil` then no specific condition is applied
				condition = nil,
				write_all_buffers = false, -- write all buffers when the current one meets `condition`
				noautocmd = false, -- do not execute autocmds when saving
				lockmarks = false, -- lock marks when saving, see `:h lockmarks` for more details
				debounce_delay = 1000, -- delay after which a pending save is executed
			 -- log debug messages to 'auto-save.log' file in neovim cache directory, set to `true` to enable
				debug = false,
		},
	},
	{
		"iamcco/markdown-preview.nvim",
		cmd = { "MarkdownPreviewToggle", "MarkdownPreview", "MarkdownPreviewStop" },
		ft = { "markdown" },
		build = function() vim.fn["mkdp#util#install"]() end,
	},
	{
		"nvim-pack/nvim-spectre",
		dependencies = {
			"nvim-lua/plenary.nvim",
			"nvim-tree/nvim-web-devicons"
		}
	},
	{
		"rcarriga/nvim-dap-ui",
		config = function()
			require("neodev").setup({
				library = { plugins = { "nvim-dap-ui" }, types = true },
			})
		end,
		dependencies = {
			"mfussenegger/nvim-dap",
			"nvim-neotest/nvim-nio",
			"folke/neodev.nvim"
		}
	},

	{
		'akinsho/bufferline.nvim',
		version = "*",
		dependencies = 'nvim-tree/nvim-web-devicons',
		config = function()
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
		end,
	},

	{
		'windwp/nvim-autopairs',
		event = "InsertEnter",
		opts = {} -- this is equalent to setup({}) function
	},
	{
		'voldikss/vim-floaterm'
	},
	{
		'nvim-lualine/lualine.nvim',
		dependencies = { 'nvim-tree/nvim-web-devicons' },
		config = function()
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

			vim.api.nvim_create_augroup("lualine_augroup", { clear = true })
			vim.api.nvim_create_autocmd("User", {
				group = "lualine_augroup",
				pattern = "LspProgressStatusUpdated",
				callback = require("lualine").refresh,
			})
		end,
	},

	{
		'linrongbin16/lsp-progress.nvim',
		config = function()
			require('lsp-progress').setup()
		end,
		dependencies = { 'nvim-lualine/lualine.nvim' }
	},
	{
		'nvim-telescope/telescope.nvim', tag = '0.1.5',
		config = function()
			require('telescope').setup{
				defaults = {
					vimgrep_arguments = {
						'rg',
						'--color=never',
						'--no-heading',
						'--with-filename',
						'--line-number',
						'--column',
						'--smart-case',
						'--hidden',
					},
				}
			}
		end,
		dependencies = {
			'nvim-lua/plenary.nvim',
			'BurntSushi/ripgrep',
			{ 'nvim-telescope/telescope-fzf-native.nvim', build = 'cmake -S. -Bbuild -DCMAKE_BUILD_TYPE=Release && cmake --build build --config Release && cmake --install build --prefix build' }
		}
    },
	{
		'mfussenegger/nvim-dap'
	},
	{
		'f-person/git-blame.nvim',
		opts = {
			enabled = false,
		},
	},

	{
		'lewis6991/gitsigns.nvim',
		config = function()
			require('gitsigns').setup()

			vim.g.gitblame_date_format = '%a %d-%m-%y'
		end,
	},

	{
		"catppuccin/nvim",
		name = "catppuccin",
		priority = 1000,
		lazy = false, -- A theme should load on startup
		config = function()
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
			-- Set the colorscheme after setting it up
			vim.cmd.colorscheme "catppuccin-mocha"
		end,
	},

	{
		"bfredl/nvim-miniyank"
	},
	{
		"moll/vim-bbye"
	},
	{
		"tomtom/tcomment_vim",
		event="BufEnter"
	},
	{
		"tpope/vim-abolish",
		event="BufEnter"
	},
	{
		"preservim/tagbar",
		event="BufEnter"
	},
	{
		"folke/todo-comments.nvim",
		dependencies = { "nvim-lua/plenary.nvim" },
		opts = {
			keywords = {
				DOING = { icon = " ", color = "warning" },
				HACK = { icon = " ", color = "warning" },
			}
		},
		lazy = true,
  },
  {
		"https://gitlab.com/schrieveslaach/sonarlint.nvim.git",
		filetypes = { "php", "typescript", "javascript" },
		dependencies = { "neovim/nvim-lspconfig" },
		lazy = true,
  },
	{
		'github/copilot.vim',
	},
}
