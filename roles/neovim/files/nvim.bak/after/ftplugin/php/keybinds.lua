local wk = require("which-key")

wk.register(
	{

		["<leader>"] = {

			r = {
				name = "Refactor",
				n = {':lua RunPhpactorRefactorCommand("fix_namespace_class_name")<CR>', 'Fix class name'},
				M = {':lua require("phpactor").rpc("context_menu", {})<CR>', 'Refactor menu'},
				c = {':lua require("phpactor").rpc("copy_class", {})<CR>', 'Copy class'},
				m = {':lua require("phpactor").rpc("move_class", {})<CR>', 'Move class'},
				r = "Rename",
				f = "Format"
			},

			g = {
				name = "Generate",
				f = {':lua RunPhpactorRefactorCommand("complete_constructor")<CR>', 'Complete constructor'},
				m = {':lua RunPhpactorRefactorCommand("implement_contracts")<CR>', 'Implement methods from interface'}, -- to be tested
				i = {':lua require("phpactor").rpc("import_missing_classes", {})<CR>', 'Generate imports'},
				n = {':lua require("phpactor").rpc("new_class", {})<CR>', 'Generate new class'}
			},

			s = {
				name = "Symbol",
				s = "Info of symbol",
				d = "Find definition",
				i = "Find references",
				q = "Close"
			},

			e = {
				name = "Error",
				n = "Next",
				p = "Previous",
				i = "Info on current"
			},

			f = {
				name = "Find",
				t = {
					name = "Test",
					u = {"<cmd>lua switch_between_file_and_test('unit')<CR>", "Test"},
					i = {"<cmd>lua switch_between_file_and_test('integration')<CR>", "Test"},
					a = {"<cmd>lua switch_between_file_and_test('api')<CR>", "Test"},
				},
				r = {"<cmd>lua switch_between_interface_and_repository()<CR>", "Repository"},
				h = {"<cmd>lua switch_between_command_and_command_handler()<CR>", 'Find Command (Handler)'},
				o = {name = "Online"}
			}
		},

		['<A-b>'] = {":lua require'dap'.toggle_breakpoint()<CR>", "Debug: Toggle breakpoint"},
		['<A-E>'] = {":lua require'dap'.set_exception_breakpoints()<CR>", "Debug: Toggle exception breakpoint"},
		['<A-c>'] = {":lua require'dap'.continue()<CR>", "Debug: Continue"},
		['<A-C>'] = {":lua require'dap'.reverse_continue()<CR>", "Debug: Reverse continue"},
		['<A-o>'] = {":lua require'dap'.step_over()<CR>", "Debug: Step over"},
		['<A-O>'] = {":lua require'dap'.step_into()<CR>", "Debug: Step into"},
		['<A-p>'] = {":lua require'dap'.step_back()<CR>", "Debug: Step back"},
		['<A-i>'] = {":lua require'dap.ui.widgets'.hover()<CR>", "Debug: Info"},
		['<A-I>'] = {":lua require'dap'.run_to_cursor()<CR>", "Debug: To cursor"},
		['<A-u>'] = {":lua require'dapui'.toggle()<CR>", "Debug: Open UI"}

	}, {
		buffer = vim.api.nvim_get_current_buf(),
	}
)

