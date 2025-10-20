return {
	{ 
		"folke/snacks.nvim",
		opts = {
			dashboard = {
				enabled = false 
			},
			scroll = {
				enabled = false
			},
		} 
	},

	{
	  "nvimdev/dashboard-nvim",
	  lazy = false, -- As https://github.com/nvimdev/dashboard-nvim/pull/450, dashboard-nvim shouldn't be lazy-loaded to properly handle stdin.
	  opts = function()
		local opts = {
		  theme = "doom",
		  hide = {
			-- this is taken care of by lualine
			-- enabling this messes up the actual laststatus setting after loading a file
			statusline = false,
		  },
		  config = {
			week_header = {
				enable = true,
			},
			-- stylua: ignore
			center = {
			  {action = "Telescope project", desc = " Projects" ,icon = " ", key = "z", },
			  { action = 'lua require("persistence").select()',              desc = " Restore Session", icon = " ", key = "s" },
			  { action = 'lua LazyVim.pick.config_files()()',              desc = " Config",          icon = " ", key = "c" },
        {
          action = function()
            vim.fn.chdir(vim.fn.expand("~/notes"))
            require("telescope.builtin").find_files()
          end,
          desc = " Notes",
          icon = " ",
          key = "n",
        },
			  { action = "LazyExtras",                                     desc = " Lazy Extras",     icon = " ", key = "x" },
			  { action = "Lazy",                                           desc = " Lazy",            icon = "󰒲 ", key = "l" },
			  { action = function() vim.api.nvim_input("<cmd>qa<cr>") end, desc = " Quit",            icon = " ", key = "q" },
			},
			footer = function()
			  local stats = require("lazy").stats()
			  local ms = (math.floor(stats.startuptime * 100 + 0.5) / 100)
			  return { "⚡ Neovim loaded " .. stats.loaded .. "/" .. stats.count .. " plugins in " .. ms .. "ms" }
			end,
		  },
		}

			    if not vim.tbl_get(opts, "config", "center") then
      return
    end

		for _, button in ipairs(opts.config.center) do
		  button.desc = button.desc .. string.rep(" ", 43 - #button.desc)
		  button.key_format = "  %s"
		end

		-- open dashboard after closing lazy
		if vim.o.filetype == "lazy" then
		  vim.api.nvim_create_autocmd("WinClosed", {
			pattern = tostring(vim.api.nvim_get_current_win()),
			once = true,
			callback = function()
			  vim.schedule(function()
				vim.api.nvim_exec_autocmds("UIEnter", { group = "dashboard" })
			  end)
			end,
		  })
		end

		return opts
	  end,
	}
}
