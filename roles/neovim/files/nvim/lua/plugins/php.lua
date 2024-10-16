return {
	{
		"gbprod/phpactor.nvim",
		build = function()
			require("phpactor.handler.update")()
		end,
		dependencies = {
			"nvim-lua/plenary.nvim",
			"neovim/nvim-lspconfig"
		},
		opts = {
		},
		ft = "php",
	},
	{
		"alvan/vim-php-manual",
	}
}
