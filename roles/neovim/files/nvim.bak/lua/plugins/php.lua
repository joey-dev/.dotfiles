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
	},
	{
    "andythigpen/nvim-coverage",
    version = "*", -- Pin to a specific version if you prefer
    config = function()
      require("coverage").setup({
        auto_reload = true, -- Automatically reload coverage when the file changes
        auto_display = true, -- Automatically display coverage when opening a file
        highlights = {
          covered = { fg = "#C3E88D" }, -- Green
          uncovered = { fg = "#F07178" }, -- Red
        },
        signs = {
          covered = { text = "✓", hl = "CoverageCovered" },
          uncovered = { text = "✗", hl = "CoverageUncovered" },
        },
        lang = {
          php = {
            -- This path MUST match the outputFile in your phpunit.xml
            coverage_file = "legacy/--config=phpunit.xml.dist",
          },
        },
      })
    end,
    dependencies = { "nvim-lua/plenary.nvim" },
  }
}
