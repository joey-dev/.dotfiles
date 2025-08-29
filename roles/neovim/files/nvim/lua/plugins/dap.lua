-- ~/.config/nvim/lua/plugins/dap.lua
return {
  {
    "mfussenegger/nvim-dap",
    dependencies = {
      "rcarriga/nvim-dap-ui",
      "nvim-neotest/nvim-nio",
    },
    -- THE FIX: We define all keymaps in this 'keys' table.
    -- LazyVim will automatically load the plugin when any of these keys are pressed.
    keys = {
      { "<leader>d", group = "Debug" }, -- This creates the menu group in which-key
      { "<leader>db", function() require("dap").toggle_breakpoint() end, desc = "Breakpoint" },
      { "<leader>dc", function() require("dap").continue() end,       desc = "Continue" },
      { "<leader>di", function() require("dap").step_into() end,      desc = "Step Into" },
      { "<leader>dl", function() require("dap").run_last() end,        desc = "Launch" },
      { "<leader>do", function() require("dap").step_over() end,      desc = "Step Over" },
      { "<leader>dO", function() require("dap").step_out() end,       desc = "Step Out" },
      { "<leader>du", function() require("dapui").toggle() end,        desc = "Toggle UI" },
      { "<leader>dB", function() require("dap").set_breakpoint(vim.fn.input("Condition: ")) end, desc = "Conditional Breakpoint" },
    },
    config = function()
      -- The config function is now much cleaner and only contains setup logic.
      local dap = require("dap")
      local dapui = require("dapui")

      dap.adapters.php = {
        type = "executable",
        command = "node",
        args = { os.getenv("HOME") .. "/vscode-php-debug/out/phpDebug.js" },
      }

      dap.configurations.php = {
        {
          type = "php",
          request = "launch",
          name = "Listen for Xdebug",
          port = 9003,
          pathMappings = { ["/var/www/html"] = "${workspaceFolder}" },
        },
      }

      dapui.setup()
    end,
  },
}
