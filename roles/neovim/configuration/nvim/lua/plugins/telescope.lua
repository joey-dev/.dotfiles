
return {
  {
    'nvim-telescope/telescope.nvim',
    event = "VimEnter", -- Load Telescope on startup
    dependencies = {
      'nvim-lua/plenary.nvim',
      -- Add the new project plugin as a dependency
      { "nvim-telescope/telescope-project.nvim" },
    },
    config = function()
      local telescope = require('telescope')

      -- Configure Telescope and the new project extension
      telescope.setup({
        extensions = {
          project = {
            -- These are the directories it will scan for your git projects
            base_dirs = {
              '~/Code/Work',
              '~/Code/Learning',
              '~/Code/Projects',
              '~/.dotfiles',
              '~/notes',
            },
            hidden_files = true, -- shows hidden folders like .dotfiles
            theme = "dropdown",
          },
        },
      })

      -- Load the new extension
      telescope.load_extension("project")
    end,
  },
}
