return {
	{
		"coffebar/neovim-project",
		opts = {
			projects = {
				"~/Code/Work/*",
				"~/Code/Learning/*",
				"~/Code/Projects/*",
				"~/.dotfiles",
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
					},
					footer = {}  --your footer
				}
			}
		end,
		dependencies = { {'nvim-tree/nvim-web-devicons'}}
	},
	{
		"nvim-neo-tree/neo-tree.nvim",
		branch = "v3.x",
		dependencies = {
		  "nvim-lua/plenary.nvim",
		  "nvim-tree/nvim-web-devicons",
		  "MunifTanjim/nui.nvim",
		  "3rd/image.nvim",
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
		"iamcco/markdown-preview.nvim",
		cmd = { "MarkdownPreviewToggle", "MarkdownPreview", "MarkdownPreviewStop" },
		ft = { "markdown" },
		build = function() vim.fn["mkdp#util#install"]() end,
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
