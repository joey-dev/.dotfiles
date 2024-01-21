local vim = vim
local execute = vim.api.nvim_command
local fn = vim.fn

vim.g.mapleader = " "

vim.cmd("language en_US.utf8")
vim.api.nvim_set_keymap("", "<Space>", "<Nop>", { noremap = true })

require("plugins")

vim.api.nvim_set_keymap("n", "<leader>vi", ":e ~/.dotfiles/roles/neovim/files/config/init.lua<cr>", { noremap = true })
vim.api.nvim_set_keymap("n", "<leader>vs", ":source ~/.dotfiles/roles/neovim/files/config/init.lua<cr>", { noremap = true })

-- nvim settings
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


-- global keymap
-- projects
vim.keymap.set('n', '<Leader>pl', ':ProjectList<cr>')
vim.keymap.set('n', '<Leader>fif', ':ProjectFindInFiles<cr>')
vim.keymap.set('n', '<Leader>ff', ':ProjectSearchFiles<cr>')

-- task manager
vim.keymap.set('n', '<Leader>tm', ':ProjectRun<cr>')

-- tree
vim.keymap.set('n', '<Leader>pf', ':Neotree<cr>')
vim.keymap.set('n', '<Leader>pcf', ':Neotree reveal<cr>')
vim.keymap.set('n', '<Leader>pof', ':Neotree buffers<cr>')

--- git
vim.keymap.set('n', '<Leader>gs', ':Neotree git_status<cr>')

-- view
vim.keymap.set('n', '<Leader>vm', ':MarkdownPreview<cr>')
vim.keymap.set('n', '<Leader>vM', ':MarkdownPreviewStop<cr>')
