-- Keymaps are automatically loaded on the VeryLazy event
-- Default keymaps that are always set: https://github.com/LazyVim/LazyVim/blob/main/lua/lazyvim/config/keymaps.lua
-- Add any additional keymaps here

local map = LazyVim.safe_keymap_set

map("n", "<M-q>", "<cmd>bprevious<cr>", { desc = "Prev Buffer" })
map("n", "<M-e>", "<cmd>bnext<cr>", { desc = "Next Buffer" })
map("n", "<M-w>", function()
  Snacks.bufdelete()
end, { desc = "Delete Buffer" })

map("n", "<Leader>ci", function()
  -- Get the Phpactor LSP client specifically
  local phpactor_client = vim.lsp.get_active_clients({ bufnr = 0, name = "phpactor" })[1]

  if not phpactor_client then
    vim.notify("Phpactor LSP client not active for this buffer.", vim.log.levels.WARN)
    return
  end

  local uri = vim.uri_from_bufnr(0)

  -- Execute the Phpactor command, targeting only the Phpactor client
  phpactor_client.request("workspace/executeCommand", {
    command = "import_all_unresolved_names",
    arguments = { uri },
  })
end, { desc = "Generate imports" })

-- ==========================================
-- CUSTOM PHPUNIT DOCKER RUNNER
-- ==========================================

local function run_phpunit(is_debug, specific_method, skip_rebuild)
  local filepath = vim.fn.expand("%")

  if filepath == "" then
    vim.notify("Cannot run PHPUnit for an unsaved buffer. Save the file first.", vim.log.levels.WARN)
    return
  end

  local suite = filepath:match("^legacy/tests/([^/]+)/") or "unit"

  local clean_path = filepath
  if suite == "unit" then
    clean_path = filepath:gsub("^legacy/", "")
  else
    local pattern = "^legacy/tests/" .. suite .. "/"
    clean_path = filepath:gsub(pattern, "")
  end

  -- Build the flags
  local debug_flag = is_debug and "debug " or ""
  local rebuild_flag = ""

  -- Only inject the flag if requested AND we are in the api/integration suites
  if skip_rebuild and (suite == "integration" or suite == "api") then
    rebuild_flag = " --no-rebuild "
  end

  local cmd = string.format("./test_runner.sh %s%s%s %s", debug_flag, suite, rebuild_flag, clean_path)

  if specific_method then
    local current_node = vim.treesitter.get_node()
    local method_name = nil

    while current_node do
      if current_node:type() == "method_declaration" then
        for child in current_node:iter_children() do
          if child:type() == "name" then
            method_name = vim.treesitter.get_node_text(child, 0)
            break
          end
        end
      end
      if method_name then
        break
      end
      current_node = current_node:parent()
    end

    if method_name then
      cmd = cmd .. " --filter " .. method_name
    else
      vim.notify("No test method found under cursor!", vim.log.levels.WARN)
      return
    end
  end

  vim.cmd("botright split | resize 15 | terminal " .. cmd)
  vim.cmd("startinsert")
end

-- ==========================================
-- THE KEYBINDS
-- ==========================================

-- FAST RUNS (Lowercase) - Skips Rebuild for API/Integration
vim.keymap.set("n", "<leader>tc", function()
  run_phpunit(false, true, true)
end, { desc = "Run Test Case (Fast)" })
vim.keymap.set("n", "<leader>tf", function()
  run_phpunit(false, false, true)
end, { desc = "Run Test File (Fast)" })
vim.keymap.set("n", "<leader>td", function()
  run_phpunit(true, true, true)
end, { desc = "Debug Test Case (Fast)" })

-- SLOW RUNS (Uppercase) - Forces Full Docker Rebuild
vim.keymap.set("n", "<leader>tC", function()
  run_phpunit(false, true, false)
end, { desc = "Run Test Case (Rebuild)" })
vim.keymap.set("n", "<leader>tF", function()
  run_phpunit(false, false, false)
end, { desc = "Run Test File (Rebuild)" })
vim.keymap.set("n", "<leader>tD", function()
  run_phpunit(true, true, false)
end, { desc = "Debug Test Case (Rebuild)" })
