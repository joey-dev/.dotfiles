local vim = vim
local execute = vim.api.nvim_command
local fn = vim.fn


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

require("lazy").setup("plugins")

-- nvim settings

-- colors

-- imports, not needed?

-- projects


--- git


-- loop through a to z

-- LSP progress bar


-- Function to get the git root directory


-- fixers/formatters

--vim.g.ale_linters = {'cspell'}

-- spectre

-- rainbow brackets

-- indent blank line
-- dashboard


-- key-binds
