return {
  -- This forcefully disables the core neotest plugin
  { "nvim-neotest/neotest", enabled = false },

  -- We also disable the PHP-specific adapter just to be safe
  { "olimorris/neotest-phpunit", enabled = false },
}
