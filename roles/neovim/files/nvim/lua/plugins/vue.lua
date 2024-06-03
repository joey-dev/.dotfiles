return {
	{
    'microsoft/vscode-js-debug',
    run = 'npm install --legacy-peer-deps && npx gulp vsDebugServerBundle && mv dist out',
  },
	{
		'mxsdev/nvim-dap-vscode-js',
		ft = "vue",
		dependencies = {
		  'mfussenegger/nvim-dap',
		},
	},
}
