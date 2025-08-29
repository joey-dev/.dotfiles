-- Bootstrap lazy.nvim (Plugin Manager)
local lazypath = vim.fn.stdpath("data") .. "/lazy/lazy.nvim"
if not vim.loop.fs_stat(lazypath) then
  vim.fn.system({
    "git",
    "clone",
    "--filter=blob:none",
    "https://github.com/folke/lazy.nvim.git",
    "--branch=stable",
    lazypath,
  })
end
vim.opt.rtp:prepend(lazypath)

-- Setup lazy.nvim, and tell it to load all files in lua/plugins/
require("lazy").setup("plugins", {
  -- You can add lazy.nvim options here, e.g., for performance
  change_detection = {
    notify = false, -- Don't show a notification when plugins are updated
  },
})

