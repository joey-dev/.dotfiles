return {
  -- This is a "dummy" plugin spec that loads early to set options and keymaps
  {
    "LazyVim/LazyVim",
    priority = 1000, -- Load this first
    config = function()
			vim.g.mapleader = " "

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

			vim.opt.termguicolors = true
			vim.fn.matchadd("GreenBang", "!")

			vim.g.ale_fixers = {'trim_whitespace', 'remove_trailing_lines'}
			vim.g.ale_fix_on_save = 1

			vim.cmd("language en_US.utf8")

			vim.api.nvim_set_keymap("", "<Space>", "<Nop>", { noremap = true })

    end,
  },
}

