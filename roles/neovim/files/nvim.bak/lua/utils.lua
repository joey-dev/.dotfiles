local M = {}

local previewers = require('telescope.previewers')

local finders = require('telescope.finders')
local pickers = require('telescope.pickers')
local sorters = require('telescope.sorters')
local actions = require('telescope.actions')
local action_state = require('telescope.actions.state')
local conf = require('telescope.config').values

local Path = require('plenary.path')

function M.get_git_root_or_nil()
  local git_root = vim.fn.systemlist("git rev-parse --show-toplevel")[1]
  if git_root == "" then
    return nil
  end
  return git_root
end

local test_groups = {"unit", "integration", "api"}

-- Function to recursively search files in a directory
local function search_files(dir)
  local results = {}
  if Path:new(dir):is_dir() then
    local p = io.popen('find "'..dir..'" -type f')
    for file in p:lines() do
      table.insert(results, file)
    end
    p:close()
  end
  return results
end

-- Function to extract @group tags from a file
local function extract_groups(file)
  local groups = {}
  for line in io.lines(file) do
    local group = line:match("@group%s+(%w+)")
    if group then
      groups[group] = true
    end
  end
  return groups
end

function M.run_phpstan()
  vim.cmd(":below 10split | :terminal cd legacy && vendor/bin/phpstan analyze Core Common Component app src --memory-limit=-1 -c phpstan.neon.dist")
end

function M.run_csfix(type)
	if type == "master" then
		vim.cmd(":below 10split | :terminal bin/console cs:fix master..HEAD")
	end

	if type == "current" then
		vim.cmd(":below 10split | :terminal bin/cs.php fix")
	end
end

function M.run_database_import()
	vim.ui.input({ prompt = 'Enter database name: ' }, function(input)
		vim.cmd("!bin/db i " .. input)
	end)
end

local function get_customers_list()
  local output = vim.fn.systemlist("bin/db customers | tail -n +2 | awk -F'|' '{print $2}' | sed 's/^ *//; s/ *$//' | grep -v '^$' | grep -v '^Name$'")
  return output
end

local function get_customer_databases_list()
  local output = vim.fn.systemlist("bin/db customers | tail -n +2 | awk -F'|' '{print $3}' | sed 's/^ *//; s/ *$//' | grep -v '^$' | grep -v '^Database$'")
  return output
end

local function get_customers_url_list()
  local output = vim.fn.systemlist("bin/db customers | tail -n +2 | awk -F'|' '{print $4}' | sed 's/^ *//; s/ *$//' | grep -v '^$' | grep -v '^Url$'")
  return output
end

function M.create_new_migration()
  vim.cmd(string.format(":below 10split | :terminal bin/console db:migration:init"))
end

function M.run_database_migration()
  local opts = {}
  local customers = get_customers_list()

  pickers.new(opts, {
    prompt_title = "Customers",
    finder = finders.new_table {
      results = customers
    },
    sorter = conf.generic_sorter(opts),
    attach_mappings = function(prompt_bufnr, map)
      actions.select_default:replace(function()
        actions.close(prompt_bufnr)
        local selection = action_state.get_selected_entry()
        local name = selection[1]
        vim.cmd('!bin/db m ' .. name)
      end)
      return true
    end,
  }):find()
end

function M.php_clear_cache()
	vim.cdm('cd legacy && bin/console cache:clear');
end

function M.run_database_delete()
  local opts = {}
  local customers = get_customer_databases_list()

  pickers.new(opts, {
    prompt_title = "Customers",
    finder = finders.new_table {
      results = customers
    },
    sorter = conf.generic_sorter(opts),
    attach_mappings = function(prompt_bufnr, map)
      actions.select_default:replace(function()
        actions.close(prompt_bufnr)
        local selection = action_state.get_selected_entry()
        local name = selection[1]
        vim.cmd('!bin/db db:drop ' .. name)
      end)
      return true
    end,
  }):find()
end

function M.run_database_customer_url()
  local opts = {}
  local customers = get_customers_list()

  pickers.new(opts, {
    prompt_title = "Customers",
    finder = finders.new_table {
      results = customers
    },
    sorter = conf.generic_sorter(opts),
    attach_mappings = function(prompt_bufnr, map)
      actions.select_default:replace(function()
        actions.close(prompt_bufnr)
        local selection = action_state.get_selected_entry()
        local name = selection[1]
				local url = "https://dyflexis.dev.wodanbrothers.com/" .. name;
				os.execute("xdg-open " .. url)

      end)
      return true
    end,
  }):find()
end

function M.search_and_display_groups(post_fix)
  local git_root = get_git_root_or_nil()
  if not git_root then
    vim.api.nvim_err_writeln("Error: Not a git repository or unable to find git root.")
    return
  end

  local results = {}

  -- Add predefined options
  table.insert(results, "current file")
  table.insert(results, "all unit")
  table.insert(results, "all integration")
  table.insert(results, "all api")

  for _, group in ipairs(test_groups) do
    local path = git_root .. "/legacy/tests/" .. group
    local files = search_files(path)
    local group_results = {}

    for _, file in ipairs(files) do
      local groups = extract_groups(file)
      for word in pairs(groups) do
        group_results[word] = true
      end
    end

    for word in pairs(group_results) do
      table.insert(results, group .. " " .. word)
    end
  end

  if vim.tbl_isempty(results) then
    vim.api.nvim_err_writeln("Warning: No test groups found. Showing predefined commands.")
  end

  pickers.new({}, {
    prompt_title = "Select Test Group",
    finder = finders.new_table {
      results = results
    },
    sorter = sorters.get_generic_fuzzy_sorter(),
    attach_mappings = function(prompt_bufnr, map)
      map('i', '<CR>', function()
        local selection = action_state.get_selected_entry()
        actions.close(prompt_bufnr)
        local selected = selection[1]
        local test_group, word = selected:match("^(%S+) (%S+)$")

        -- Determine the command to run based on the selection
        local command
        if selected == "current file" then
          command = find_test_command_from_current_file()
        elseif selected == "all unit" then
          command = "./test_runner.sh unit"
        elseif selected == "all integration" then
          command = "./test_runner.sh integration"
        elseif selected == "all api" then
          command = "./test_runner.sh api"
        else
          command = string.format("./test_runner.sh debug %s --group %s", test_group, word)
        end


				local formatted_post_fix
				if test_group == "unit" then
					formatted_post_fix = post_fix:gsub("%s*%-%-no%-rebuild%s*", "")
				else
					formatted_post_fix = post_fix
				end

        vim.cmd(string.format(":below 10split | :terminal %s %s", command, formatted_post_fix))
      end)
      return true
    end,
  }):find()
end

function M.find_test_command_from_current_file()
    -- Get the current file path
    local current_file = vim.fn.expand('%:p')
    local current_file_name = vim.fn.expand('%:t')

    -- Define the test groups to look for
    local test_groups = { 'unit', 'integration', 'api' }

    -- Function to find the test group in the path
    local function find_test_group(path, groups)
        for _, group in ipairs(groups) do
            if path:find(group) then
                return group
            end
        end
        return nil
    end

    -- Find the test group
    local test_group = find_test_group(current_file, test_groups)

    if not test_group then
        print('No test group found in the current path')
        return
    end

    -- Get the path from test group to the current file
    local test_path = current_file:match(test_group .. '/(.*)')

    if test_group == 'integration' or test_group == 'api' then
        if test_path and test_path:sub(1, 1) == '/' then
            test_path = test_path:sub(2)
        end
        return string.format('./test_runner.sh %s %s', test_group, test_path)
    elseif test_group == 'unit' then
        return string.format('./test_runner.sh unit --filter %s', current_file_name)
    end
end

function M.delete_session()
  local sessions_dir = vim.fn.expand('~/.local/share/nvim/neovim-sessions/')

  local session_files = vim.fn.globpath(sessions_dir, '*', false, true)

  pickers.new({}, {
    prompt_title = 'Neovim Sessions',
    finder = finders.new_table({
      results = session_files,
    }),
    sorter = conf.generic_sorter({}),
    previewer = previewers.cat.new({}),
    attach_mappings = function(prompt_bufnr, map)
      map('i', '<CR>', function()
        local selection = action_state.get_selected_entry()
        actions.close(prompt_bufnr)

        vim.fn.system({'rm', '-rf', selection[1]})
      end)
      return true
    end,
  }):find()
end

return M
