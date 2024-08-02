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
					},
					footer = {}  --your footer
				}
			}
		end,
		dependencies = { {'nvim-tree/nvim-web-devicons'}}
	},
	{
		"HiPhish/rainbow-delimiters.nvim",
		dependencies = { { 'nvim-treesitter/nvim-treesitter'}}
	},
	{
		"nvim-treesitter/nvim-treesitter",
		build = ":TSUpdate",
		config = function()
			require("nvim-treesitter.configs").setup {
				ensure_installed = { "php", "javascript", "vue", "lua", "sql", "css", "scss" },
				highlight = {
					enable = true,
					additional_vim_regex_highlighting = true,
				},
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
		"lukas-reineke/indent-blankline.nvim", main = "ibl", opts = {}
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
	},
	{
		"okuuva/auto-save.nvim",
		cmd = "ASToggle", -- optional for lazy loading on command
		event = { "InsertLeave", "TextChanged" }, -- optional for lazy loading on trigger events
		opts = {
			{
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
					immediate_save = { "BufLeave", "FocusLost" }, -- vim events that trigger an immediate save
					defer_save = { "InsertLeave", "TextChanged" }, -- vim events that trigger a deferred save (saves after `debounce_delay`)
					cancel_defered_save = { "InsertEnter" }, -- vim events that cancel a pending deferred save
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
			}
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
		dependencies = 'nvim-tree/nvim-web-devicons'
	},
	{
	  "VonHeikemen/lsp-zero.nvim",
	  dependencies = {
			-- LSP Support
			{"neovim/nvim-lspconfig"},
			{"williamboman/mason.nvim"},
			{"williamboman/mason-lspconfig.nvim"},

			-- Autocompletion
			{"hrsh7th/nvim-cmp", event = "InsertEnter"},
			{"hrsh7th/cmp-buffer"},
			{"hrsh7th/cmp-path"},
			{"saadparwaiz1/cmp_luasnip"},
			{"hrsh7th/cmp-nvim-lsp"},
			{"hrsh7th/cmp-nvim-lua"},

			-- Snippets
			{"L3MON4D3/LuaSnip", event = "InsertEnter"},
			{"honza/vim-snippets"},
	  },
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
		dependencies = { 'nvim-tree/nvim-web-devicons' }
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
		'lewis6991/gitsigns.nvim'
	},
	{
		"catppuccin/nvim", name = "catppuccin", priority = 1000
	},
	{
		"dense-analysis/ale"
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
		}
  }
}
