return {
  { "olimorris/neotest-phpunit" },
  {
    "nvim-neotest/neotest",
    opts = { 
      adapters = { "neotest-phpunit" },
      root = function()
        -- This command finds the top-level directory of your git repo
        local git_root = vim.fn.systemlist("git rev-parse --show-toplevel")[1]

        -- If a git root is found, append '/legacy' to it
        if git_root and git_root ~= "" then
          return git_root .. "/legacy"
        end

        -- Otherwise, use the default behavior
        return nil
        end,
    },
  },
}
