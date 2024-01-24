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


vim.g.mapleader = " "

require("lazy").setup({
	"leafOfTree/vim-project",
	{
		"ThePrimeagen/harpoon",
		branch = "harpoon2",
		dependencies = { "nvim-lua/plenary.nvim" }
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
				position = "float",
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
		{"rafamadriz/friendly-snippets"},
	  },
	},
	{
		'gbprod/phpactor.nvim',
		build = function() require('phpactor.handler.update') end, -- To install/update phpactor when installing this plugin
		opts = {
		  install = {
			bin = vim.fn.stdpath('data') .. '/mason/bin/phpactor',
		  },
		  lspconfig = {
			enabled = false,
		  },
		},
		config = function(_, opts)
		  local phpactor = require('phpactor')
		  phpactor.setup(opts)

		  vim.api.nvim_set_keymap('n', '<leader>pa', ':lua require("phpactor").rpc()<CR>', { noremap = true, silent = true })
		end,
		dependencies = {
		  'nvim-lua/plenary.nvim',
		  'neovim/nvim-lspconfig',
		},
	},
	{
		'windwp/nvim-autopairs',
		event = "InsertEnter",
		opts = {} -- this is equalent to setup({}) function
	}
})
