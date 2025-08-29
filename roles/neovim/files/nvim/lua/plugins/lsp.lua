return {
  {
    "neovim/nvim-lspconfig",
    ---@class PluginLspOpts
    opts = {
      ---@type lspconfig.options
      servers = {
        -- Ensure phpactor is started with phpstan enabled
        phpactor = {
          keys = {
            -- Add any custom keymappings here if you wish
          },
          -- This is the important part
          settings = {
            ["phpactor.phpstan.enabled"] = true,
            ["phpactor.diagnostics.enabled"] = true,
            ["phpactor.language_server_phpstan.enabled"] = true, -- For newer versions of the extension
          },
        },
      },
    },
  },
}
