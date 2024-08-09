-- wanted:
-- PhpactorExtractExpression
-- PhpactorExtractMethod

local vim = vim
local execute = vim.api.nvim_command
local fn = vim.fn
local lsp = require("lsp-zero")
local api = vim.api

-- phpactor
vim.api.nvim_create_autocmd('LspAttach', {
  desc = 'LSP actions',
  callback = function(event)
    local opts = {buffer = event.buf}

    vim.keymap.set('n', '<leader>ss', '<cmd>lua vim.lsp.buf.hover()<cr>', opts)
    vim.keymap.set('n', '<leader>sd', '<cmd>lua vim.lsp.buf.definition()<cr>', opts)
    vim.keymap.set('n', '<leader>si', '<cmd>lua vim.lsp.buf.references()<cr>', opts)
    vim.keymap.set('n', '<leader>rr', '<cmd>lua vim.lsp.buf.rename()<cr>', opts)
    vim.keymap.set({'n', 'x'}, '<leader>rf', '<cmd>lua vim.lsp.buf.format({async = true})<cr>', opts)
    vim.keymap.set('n', '<leader>ei', '<cmd>lua vim.diagnostic.open_float()<cr>', opts)
    vim.keymap.set('n', '<leader>en', '<cmd>lua vim.diagnostic.goto_prev()<cr>', opts)
    vim.keymap.set('n', '<leader>ep', '<cmd>lua vim.diagnostic.goto_next()<cr>', opts)
    vim.keymap.set('n', '<leader>sq', ':cclose<CR>', opts)
  end
})

vim.b.ale_linters = {php = {'phpmd', 'phpstan', 'cspell'}}
vim.b.ale_fixers = {php = {'php_cs_fixer'}}
vim.g.ale_fix_on_save = 1


-- phpmd
vim.g.ale_php_phpmd_executable = os.getenv("HOME") .. '/.config/composer/vendor/bin/phpmd'
vim.g.ale_php_phpmd_ruleset = os.getenv("HOME") .. '/.dotfiles/roles/neovim/files/phpmd_ruleset.xml'

-- phpcs
vim.g.ale_php_cs_fixer_executable = os.getenv("HOME") .. '/Code/Work/dyflexis-monorepo/tools/vendor/bin/php-cs-fixer'
vim.g.ale_php_cs_fixer_options= "--config='/home/joey/Code/Work/dyflexis-monorepo/tools/.php-cs-fixer.php'"

-- phpstan
local function find_project_root()
    local path = vim.fn.expand('%:p:h') -- Get the directory of the current file
    while path ~= '/' do -- Stop when reaching the root directory
        if vim.fn.filereadable(path .. '/composer.json') == 1 then
            return path
        end
        path = vim.fn.fnamemodify(path, ':h') -- Move up one directory
    end
    return vim.fn.getcwd() -- If no composer.json found, return the current working directory
end

local function find_phpstan_neon(root_path)
    local phpstan_neon_path = root_path .. '/phpstan.neon'
    if vim.fn.filereadable(phpstan_neon_path) == 1 then
        return phpstan_neon_path
    else
        return os.getenv("HOME") .. '/.dotfiles/roles/neovim/files/phpstan_configuration.neon'
    end
end

local project_root = find_project_root()

vim.g.ale_php_phpstan_executable = os.getenv("HOME") .. '/.config/composer/vendor/bin/phpstan'
vim.g.ale_php_phpstan_configuration = find_phpstan_neon(project_root)
vim.g.ale_php_phpstan_autoload = project_root .. '/vendor/autoload.php'
vim.g.ale_php_phpstan_use_global = 1


-- mason

local lspconfig = require('lspconfig')
require('mason').setup({})
require'lspconfig'.phpactor.setup{}
require("mason-lspconfig").setup({
    ensure_installed = {"phpactor"},
})


vim.lsp.set_log_level("debug")

local configs = require('lspconfig.configs')
local nvim_lsp = require('lspconfig')

require('sonarlint').setup({
   server = {
      cmd = {
         'sonarlint-language-server',
         '-stdio',
         '-analyzers',
         vim.fn.expand("$MASON/share/sonarlint-analyzers/sonarphp.jar"),
      },
			settings = {
         sonarlint = {
            rules = {
							["php:S2011"] = { level = "on" },
							["php:S4721"] = { level = "on" },
							["php:S2042"] = { level = "on", parameters = { maximumLinesThreshold = 200 } },
							["php:S1135"] = { level = "on" },
							["php:S5708"] = { level = "on" },
							["php:S1176"] = { level = "on" },
							["php:S2044"] = { level = "on" },
							["php:S836"] = { level = "on" },
							["php:S4823"] = { level = "on" },
							["php:S3275"] = { level = "on" },
							["php:S2053"] = { level = "on" },
							["php:S881"] = { level = "on" },
							["php:S3331"] = { level = "on" },
							["php:S5996"] = { level = "on" },
							["php:S2014"] = { level = "on" },
							["php:S2701"] = { level = "on" },
							["php:S6395"] = { level = "on" },
							["php:S3334"] = { level = "on" },
							["php:S5146"] = { level = "on" },
							["php:S3337"] = { level = "on" },
							["php:S121"] = { level = "on" },
							["php:S1117"] = { level = "on" },
							["php:S6323"] = { level = "on" },
							["php:S1613"] = { level = "on" },
							["php:S1603"] = { level = "on" },
							["php:S3801"] = { level = "on" },
							["php:S2918"] = { level = "on" },
							["php:S126"] = { level = "on" },
							["php:S1172"] = { level = "on" },
							["php:S5122"] = { level = "on" },
							["php:S134"] = { level = "on", parameters = { max = 3 } },
							["php:S2068"] = { level = "on", parameters = { credentialWords = password, passwd, pwd, passphrase } },
							["php:S1997"] = { level = "on" },
							["php:S2251"] = { level = "on" },
							["php:S4036"] = { level = "on" },
							["php:S1106"] = { level = "off" }, -- curly brace if statement to the end
							["php:S6393"] = { level = "on" },
							["php:S2575"] = { level = "on" },
							["php:S1848"] = { level = "on" },
							["php:S3336"] = { level = "on" },
							["php:S1482"] = { level = "on", parameters = { minimumBranchCoverageRatio = 65.0 } },
							["php:S3335"] = { level = "on" },
							["php:S2681"] = { level = "on" },
							["php:S5935"] = { level = "on" },
							["php:S103"] = { level = "on", parameters = { maximumLineLength = 120 } },
							["php:S2078"] = { level = "on" },
							["php:S3424"] = { level = "on" },
							["php:S5868"] = { level = "on" },
							["php:S1121"] = { level = "on" },
							["php:S3763"] = { level = "on" },
							["php:S1999"] = { level = "on" },
							["php:S101"] = { level = "on" },
							["php:S1607"] = { level = "on" },
							["php:S1226"] = { level = "on" },
							["php:S1144"] = { level = "on" },
							["php:S3330"] = { level = "on" },
							["php:S5131"] = { level = "on" },
							["php:S1067"] = { level = "on", parameters = { max = 3 } },
							["php:S2002"] = { level = "on" },
							["php:S2699"] = { level = "on" },
							["php:S2123"] = { level = "on" },
							["php:S131"] = { level = "on" },
							["php:S1484"] = { level = "on", parameters = { minimumCommentDensity = 25.0 } },
							["php:S4508"] = { level = "on" },
							["php:S2662"] = { level = "on" },
							["php:S3502"] = { level = "on" },
							["php:S4524"] = { level = "on" },
							["php:S6331"] = { level = "on" },
							["php:S5542"] = { level = "on" },
							["php:S5334"] = { level = "on" },
							["php:S1313"] = { level = "on" },
							["php:S138"] = { level = "on", parameters = { max = 100 } },
							["php:S1145"] = { level = "on" },
							["php:S1155"] = { level = "on" },
							["php:S1488"] = { level = "on" },
							["php:S6002"] = { level = "on" },
							["php:S1481"] = { level = "off" }, -- already exists
							["php:S2260"] = { level = "on" },
							["php:S5332"] = { level = "on" },
							["php:S4818"] = { level = "on" },
							["php:S3981"] = { level = "on" },
							["php:S1477"] = { level = "on" },
							["php:S2255"] = { level = "on" },
							["php:S3626"] = { level = "on" },
							["php:S112"] = { level = "on" },
							["php:S2001"] = { level = "on" },
							["php:S1765"] = { level = "on" },
							["php:S4426"] = { level = "on" },
							["php:S122"] = { level = "on" },
							["php:S105"] = { level = "on" },
							["php:S6348"] = { level = "on" },
							["php:S1781"] = { level = "on" },
							["php:S930"] = { level = "on" },
							["php:S6394"] = { level = "on" },
							["php:S1200"] = { level = "on", parameters = { max = 20 } },
							["php:S1780"] = { level = "on" },
							["php:S108"] = { level = "on" },
							["php:S907"] = { level = "on" },
							["php:S3288"] = { level = "on" },
							["php:S4502"] = { level = "on" },
							["php:S5547"] = { level = "on" },
							["php:S1264"] = { level = "on" },
							["php:S5145"] = { level = "on" },
							["php:S6342"] = { level = "on" },
							["php:S6397"] = { level = "on" },
							["php:S1075"] = { level = "on" },
							["php:S4828"] = { level = "on" },
							["php:S5167"] = { level = "on" },
							["php:S3649"] = { level = "on" },
							["php:S1764"] = { level = "on" },
							["php:S2737"] = { level = "on" },
							["php:S6328"] = { level = "on" },
							["php:S3338"] = { level = "on" },
							["php:S128"] = { level = "on" },
							["php:S5783"] = { level = "on" },
							["php:S1871"] = { level = "on" },
							["php:S1126"] = { level = "on" },
							["php:S2495"] = { level = "on" },
							["php:S4507"] = { level = "on" },
							["php:S2425"] = { level = "on" },
							["php:S3699"] = { level = "on" },
							["php:S1940"] = { level = "on" },
							["php:S5842"] = { level = "on" },
							["php:S6326"] = { level = "on" },
							["php:S6396"] = { level = "on" },
							["php:S3045"] = { level = "on" },
							["php:S1045"] = { level = "on" },
							["php:S1134"] = { level = "on" },
							["php:S125"] = { level = "on" },
							["php:S1789"] = { level = "on" },
							["php:S1799"] = { level = "on" },
							["php:S5867"] = { level = "on" },
							["php:S1788"] = { level = "on" },
							["php:S1808"] = { level = "on" }, -- for code quality based on PSR
							["php:S1700"] = { level = "on" },
							["php:S2234"] = { level = "on" },
							["php:S6345"] = { level = "on" },
							["php:S1483"] = { level = "on", parameters = { minimumLineCoverageRatio = 65.0 } },
							["php:S1606"] = { level = "on" },
							["php:S5361"] = { level = "on" },
							["php:S2048"] = { level = "on" },
							["php:S1451"] = { level = "on" },
							["php:S5843"] = { level = "on", parameters = { maxComplexity = 20 } },
							["php:S3287"] = { level = "on" },
							["php:S1763"] = { level = "on" },
							["php:S5994"] = { level = "on" },
							["php:S3776"] = { level = "on", parameters = { threshold = 15 } },
							["php:S2050"] = { level = "on" },
							["php:S4790"] = { level = "on" },
							["php:S5713"] = { level = "on" },
							["php:S2761"] = { level = "on" },
							["php:S905"] = { level = "on" },
							["php:S3955"] = { level = "on" },
							["php:S3332"] = { level = "on" },
							["php:S1068"] = { level = "on" },
							["php:S1757"] = { level = "on" },
							["php:S2755"] = { level = "on" },
							["php:S4817"] = { level = "on" },
							["php:S2595"] = { level = "on" },
							["php:S5850"] = { level = "on" },
							["php:S6341"] = { level = "on" },
							["php:S1125"] = { level = "on" },
							["php:S2651"] = { level = "on" },
							["php:S1784"] = { level = "on" },
							["php:S2004"] = { level = "on" },
							["php:S5527"] = { level = "on" },
							["php:S2007"] = { level = "on" },
							["php:S2751"] = { level = "on" },
							["php:S110"] = { level = "on", parameters = { max = 5, filteredClasses = "" } },
							["php:S4529"] = { level = "on" },
							["php:S6353"] = { level = "on" },
							["php:S3255"] = { level = "on" },
							["php:S1116"] = { level = "on" },
							["php:S800"] = { level = "on" },
							["php:S2830"] = { level = "on" },
							["php:S3772"] = { level = "on" },
							["php:S5899"] = { level = "on" },
							["php:S2037"] = { level = "on" },
							["php:S1192"] = { level = "on", parameters = { threshold = 3 } },
							["php:S3923"] = { level = "on" },
							["php:S6001"] = { level = "on" },
							["php:S104"] = { level = "on", parameters = { max = 1000 } }, -- was broken
							["php:S4830"] = { level = "on" },
							["php:S1314"] = { level = "on" },
							["php:S4784"] = { level = "on" },
							["php:S1677"] = { level = "on" },
							["php:S3972"] = { level = "on" },
							["php:S1131"] = { level = "on" },
							["php:S1185"] = { level = "on" },
							["php:S2077"] = { level = "on" },
							["php:S6600"] = { level = "on" },
							["php:S2076"] = { level = "on" },
							["php:S1448"] = { level = "on", parameters = { maximumMethodThreshold = 35, countNonpublicMethods = true } },
							["php:S6344"] = { level = "on" },
							["php:S2070"] = { level = "on" },
							["php:S2003"] = { level = "on" },
							["php:S4787"] = { level = "on" },
							["php:S4143"] = { level = "on" },
							["php:S2277"] = { level = "on" },
							["php:S1142"] = { level = "on", parameters = { max = 3 } },
							["php:S1536"] = { level = "on" },
							["php:S1697"] = { level = "on" },
							["php:S2091"] = { level = "on" },
							["php:S6173"] = { level = "on" },
							["php:S5144"] = { level = "on" },
							["php:S1821"] = { level = "on" },
							["php:S1605"] = { level = "on" },
							["php:S2608"] = { level = "on" },
							["php:S5247"] = { level = "on" },
							["php:S4284"] = { level = "on" },
							["php:S4792"] = { level = "on" },
							["php:S5785"] = { level = "on" },
							["php:S1990"] = { level = "on" },
							["php:S2115"] = { level = "on" },
							["php:S6035"] = { level = "on" },
							["php:S127"] = { level = "on" }, -- was broken
							["php:S4797"] = { level = "on" },
							["php:S1820"] = { level = "on", parameters = { maximumFieldThreshold = 20, countNonpublicFields = true } },
							["php:S5869"] = { level = "on" },
							["php:S6346"] = { level = "on" },
							["php:S3360"] = { level = "on" },
							["php:S2041"] = { level = "on" },
							["php:S2083"] = { level = "on" },
							["php:S1751"] = { level = "on" },
							["php:S5693"] = { level = "on", parameters = { fileUploadSizeLimit = 8000000, standardSizeLimit = 2000000 } },
							["php:S1995"] = { level = "on" },
							["php:S1124"] = { level = "on" },
							["php:S2000"] = { level = "on" },
							["php:S5911"] = { level = "on" },
							["php:S2612"] = { level = "on" },
							["php:S1109"] = { level = "on" },
							["php:S5863"] = { level = "on" },
							["php:S107"] = { level = "on", parameters = { max = 7, constructorMax = 7 } },
							["php:S5335"] = { level = "on" },
							["php:S3554"] = { level = "on" },
							["php:S1066"] = { level = "on" },
							["php:S2245"] = { level = "on" },
							["php:S6287"] = { level = "on" },
							["php:S5328"] = { level = "on" },
							["php:S1151"] = { level = "on", parameters = { max = 5 } },
							["php:S117"] = { level = "off", parameters = { format = "^[a-z][a-zA-Z0-9]*$"  } }, -- already exists
							["php:S5808"] = { level = "on" },
							["php:S2126"] = { level = "on" },
							["php:S2964"] = { level = "on" },
							["php:S5135"] = { level = "on" },
							["php:S2224"] = { level = "on" },
							["php:S113"] = { level = "on" },
							["php:S1186"] = { level = "on" },
							["php:S1996"] = { level = "on" },
							["php:S4825"] = { level = "on" },
							["php:S2043"] = { level = "on" },
							["php:S4824"] = { level = "on" },
							["php:S2631"] = { level = "on" },
							["php:S2630"] = { level = "on" },
							["php:S2005"] = { level = "on" },
							["php:S1793"] = { level = "on" },
							["php:S3984"] = { level = "on" },
							["php:S3477"] = { level = "on" },
							["php:S1656"] = { level = "on" },
							["php:S1541"] = { level = "on", parameters = { threshold = 10 } }, -- was broken
							["php:S5779"] = { level = "on" },
							["php:S6343"] = { level = "on" },
							["php:S4834"] = { level = "on" },
							["php:S115"] = { level = "on" },
							["php:S1301"] = { level = "on" },
							["php:S2046"] = { level = "on" },
							["php:S4144"] = { level = "on" },
							["php:S1766"] = { level = "on" },
							["php:S2757"] = { level = "on" },
							["php:S2015"] = { level = "on" },
							["php:S1600"] = { level = "on" },
							["php:S1291"] = { level = "on" },
							["php:S5632"] = { level = "on" },
							["php:S2038"] = { level = "on" },
							["php:S1523"] = { level = "on" },
							["php:S2187"] = { level = "on" },
							["php:S5915"] = { level = "on" },
							["php:S3358"] = { level = "on" },
							["php:S4142"] = { level = "on" },
							["php:S5042"] = { level = "on" },
							["php:S4423"] = { level = "on" },
							["php:S5883"] = { level = "on" },
							["php:S2010"] = { level = "on" },
							["php:S1311"] = { level = "on", parameters = { max = 200 } },
							["php:S6349"] = { level = "on" },
							["php:S1479"] = { level = "on", parameters = { max = 10 } }, -- was broken, max switch statements
							["php:S3333"] = { level = "on" },
							["php:S2278"] = { level = "on" },
							["php:S1795"] = { level = "on" },
							["php:S1862"] = { level = "on" },
							["php:S6350"] = { level = "on" },
							["php:S1779"] = { level = "on" },
							["php:S4833"] = { level = "on" },
							["php:S5856"] = { level = "on" },
							["php:S3291"] = { level = "on" },
							["php:S3415"] = { level = "on" },
							["php:S6347"] = { level = "on" },
							["php:S2036"] = { level = "on" },
							["php:S100"] = { level = "on" },
							["php:S5855"] = { level = "on" },
							["php:S1599"] = { level = "on" },
							["php:S2073"] = { level = "on" },
							["php:S1110"] = { level = "on" },
							["php:S2194"] = { level = "on" },
							["php:S1105"] = { level = "off" }, -- curly brace on same line of method opening
							["php:S4829"] = { level = "on" },
							["php:S3011"] = { level = "on" },
							["php:S4433"] = { level = "on" },
							["php:S2201"] = { level = "on" },
							["php:S5876"] = { level = "on" },
							["php:S2035"] = { level = "on" },
							["php:S2166"] = { level = "on" },
							["php:S5857"] = { level = "on" },
							["php:S3973"] = { level = "on" },
							["php:S6437"] = { level = "on" },
							["php:S6339"] = { level = "on" },
							["php:S6019"] = { level = "on" },
							["php:S1854"] = { level = "on" },
							["php:S2092"] = { level = "on" },
							["php:S2047"] = { level = "on" },
							["php:S1998"] = { level = "on" },
							["php:S139"] = { level = "on", parameters = { legalTrailingCommentPattern = "^\\s*+[^\\s]++$" } },
							["php:S114"] = { level = "on", parameters = { format = "^[A-Z][a-zA-Z0-9]*$" } },
							["php:S116"] = { level = "on", parameters = { format = "^[a-z][a-zA-Z0-9]*$" } },
							["php:S1578"] = { level = "on", parameters = { format = '[A-Z][A-Za-z0-9]+\\.[a-z]{1,3}' } }, -- format of file name
							["php:S1542"] = { level = "on", parameters = { format = "^[a-z][a-zA-Z0-9]*$" } },
            },
         },
      },
   },
	 root_dir = nvim_lsp.util.root_pattern('.git'),
   filetypes = {
      'php',
   }
})


function RunPhpactorRefactorCommand(transform_type)
  local current_file = vim.fn.shellescape(vim.fn.expand('%:p'))
  local command = string.format('phpactor class:transform %s --transform=%s', current_file, transform_type)

  local job_id = vim.fn.jobstart(command, {
    on_exit = function(_, code)
      if code == 0 then
        print('PHPactor command executed successfully')

        -- Reload the buffer to reflect changes
        vim.cmd('e')
      else
        print('PHPactor command failed with exit code:', code)
      end
    end
  })
end

-- xdebug
local dap = require('dap')

dap.adapters.php = {
  type = 'executable',
  command = 'node',
  args = { '/home/joey/vscode-php-debug/out/phpDebug.js' }
}

dap.configurations.php = {
  {
    type = 'php',
    request = 'launch',
    name = 'Listen for Xdebug',
    port = 9003,
	pathMappings = {
		["/app"] = "${workspaceFolder}/legacy",
	}
  }
}

require'dapui'.setup(
	{
    controls = {
      element = "repl",
      enabled = true,
      icons = {
        disconnect = "",
        pause = "",
        play = "",
        run_last = "",
        step_back = "",
        step_into = "",
        step_out = "",
        step_over = "",
        terminate = ""
      }
    },
    element_mappings = {},
    expand_lines = true,
    floating = {
      border = "single",
      mappings = {
        close = { "q", "<Esc>" }
      }
    },
    force_buffers = true,
    icons = {
      collapsed = "",
      current_frame = "",
      expanded = ""
    },
    layouts = {
			{
				elements = {
					{
						id = "stacks",
						size = 0.25
					},
					{
						id = "scopes",
						size = 0.5
					},
					{
						id = "breakpoints",
						size = 0.25
					},
				},
				position = "left",
				size = 40
			},
			{
				elements = {
					{
						id = "watches",
						size = 1.0
					},
				},
				position = "bottom",
				size = 10
			}
		},
    mappings = {
      edit = "e",
      expand = { "<CR>", "<2-LeftMouse>" },
      open = "o",
      remove = "d",
      repl = "r",
      toggle = "t"
    },
    render = {
      indent = 1,
      max_value_lines = 100
    }
  }
)

-- Switch between test file
function switch_between_file_and_test(test_type)
    local current_file_path = vim.fn.expand("%:p")
    local is_test_file = string.find(current_file_path, "/tests/" .. test_type .. "/") ~= nil

    if is_test_file then
        local source_file_path = string.gsub(current_file_path, "/tests/" .. test_type .. "/", "/")
        source_file_path = string.gsub(source_file_path, "Test%.php$", ".php")

        vim.cmd("edit " .. source_file_path)
    else
        local test_file_path = string.gsub(current_file_path, "Component", "tests/" .. test_type .. "/Component")
        test_file_path = string.gsub(test_file_path, "%.php$", "Test.php")

        vim.cmd("edit " .. test_file_path)
    end
end


local function file_exists(path)
  local f = io.open(path, 'r')
  if f ~= nil then io.close(f) return true else return false end
end

function switch_between_interface_and_repository()
  local current_file = api.nvim_buf_get_name(0)
  local current_dir = vim.fn.fnamemodify(current_file, ':h')
  local current_name = vim.fn.fnamemodify(current_file, ':t')
  local git_root = get_git_root_or_nil()

  local target_name
  local search_paths = {}

  if current_name:sub(1, 4) == 'Dbal' then
    target_name = current_name:sub(5)
    table.insert(search_paths, current_dir .. '/' .. target_name)
    table.insert(search_paths, current_dir .. '/../../Application/*/' .. target_name)
    table.insert(search_paths, current_dir .. '/../../Domain/*/' .. target_name)
    table.insert(search_paths, current_dir .. '/../' .. target_name)
  else
    target_name = 'Dbal' .. current_name
    table.insert(search_paths, current_dir .. '/' .. target_name)
    table.insert(search_paths, current_dir .. '/../../Infrastructure/*/' .. target_name)
    table.insert(search_paths, current_dir .. '/../' .. target_name)
  end

  if git_root then
    table.insert(search_paths, git_root .. '/' .. target_name)
    table.insert(search_paths, git_root .. '/*' .. target_name)
  end

	for _, path in ipairs(search_paths) do
    -- Using vim's glob function to expand wildcards
    local expanded_paths = vim.fn.glob(path, false, true)
    if type(expanded_paths) == 'table' then
      for _, expanded_path in ipairs(expanded_paths) do
        if file_exists(expanded_path) then
          vim.cmd('edit ' .. expanded_path)
          return
        end
      end
    elseif file_exists(expanded_paths) then
      vim.cmd('edit ' .. expanded_paths)
      return
    end
  end

  print('No related file found.')
end

