return {
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
	}
}
