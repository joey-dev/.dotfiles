local wk = require("which-key")

wk.register(
	{

		["<leader>"] = {

			r = {
				name = "Refactor",
				r = "Rename",
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
		},
	}
)

