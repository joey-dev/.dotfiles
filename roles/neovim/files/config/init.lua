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

-- plugin start
local harpoon = require("harpoon")
harpoon:setup()

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

-- buffer
vim.keymap.set("n", "<A-q>", ':bprev<cr>')
vim.keymap.set("n", "<A-e>", ':bnext<cr>')

-- harpoon
function get_git_root()
    local git_root = vim.fn.systemlist('git rev-parse --show-toplevel')[1]
    return git_root
end

function remove_current_file_from_harpoon()
    local current_file = vim.fn.expand('%:p') -- Get the full path of the current file
    local git_root = get_git_root()

    if git_root ~= '' and current_file:match(git_root) then
        local relative_path = current_file:sub(#git_root + 2) -- +2 to remove the leading '/'

		local names = harpoon:list():display()
		for i, name in ipairs(names) do
			if name == relative_path then
				print (i)
				harpoon:list():removeAt(i)
				break
			end
		end
    else
        print("Not in a Git project or unable to determine Git root.")
    end
end

vim.keymap.set("n", "<leader>mf", function() harpoon:list():append() end)
vim.keymap.set("n", "<leader>mc", function() harpoon:list():clear() end)
vim.keymap.set("n", "<leader>mr", remove_current_file_from_harpoon)
vim.keymap.set("n", "<leader>M", function() harpoon.ui:toggle_quick_menu(harpoon:list()) end)
vim.keymap.set("n", "<leader>mq", function() harpoon:list():prev() end)
vim.keymap.set("n", "<leader>me", function() harpoon:list():next() end)


