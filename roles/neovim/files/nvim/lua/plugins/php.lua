return {
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
		ft = "php",
		dependencies = {
		  'nvim-lua/plenary.nvim',
		  'neovim/nvim-lspconfig',
		},
	},
}
