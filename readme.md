# My .Dotfiles

These are all my settings and programs I use. Written in NixOS configuration for easy installation, and synchronization between different computers.

## Table of Contents
- [Getting Started](#getting_started)
- [Configuration](#configuration)
- [Commands](#commands)
- [Keybinds](#keybinds)
- [Language specific Documentation/Keybinds](#language)

## Getting Started <a name = "getting_started"></a>
Currently NixOS is supported.

### Prerequisites
- NixOS installed on your system
- Nix flakes enabled (see instructions below)

### Installation

1. Clone this repository:
```bash
git clone https://github.com/joey-dev/.dotfiles.git ~/.dotfiles
cd ~/.dotfiles
```

2. Enable flakes if not already enabled:
```bash
mkdir -p ~/.config/nix
echo "experimental-features = nix-command flakes" >> ~/.config/nix/nix.conf
```

3. Update your username in `flake.nix` (replace 'user' with your actual username)

4. Install and apply the configuration:
```bash
make install    # Add home-manager channel
make switch     # Apply the configuration
```

5. If you're using i3, logout and login again to load the new configuration.

### Available Make Commands
- `make install` - Install home-manager channel
- `make build` - Build the configuration without applying
- `make switch` - Apply the configuration
- `make update` - Update flake inputs
- `make check` - Validate the flake configuration

## Configuration <a name = "configuration"></a>
- [Neovim Snippets](#configuration_snippets)

### Neovim Snippets <a name = "configuration_snippets"></a>
To create new snippets go to the nvim/snippets directory.
The filename is: `fileType.snippets`.
If all the snippets from one filetype are also used in another filetype, use extends {fileType}.
    Example, the vue.snippets has as first line: `extends js`
A snippets looks like this:
```
snippet {snippetWord}
    {codeHere}
```

In the code you can use `${1:name}`. This will be the first item your carot goes to when selecting the snippetWord.
It starts with number 1, and goes up. number 0 will be the last one.

example:
```
snippet pubf
	public function ${1:name}(${2:params}): ${3:return}
	{
		${0:body}
	}
```


## Commands <a name = "commands"></a>
- [Todo List](#commands_todo_list)

### Todo List <a name = "commands_todo_list"></a>
- switch context (work, project): `task context work`
- add task: `task add {description of the task} +{tag} due:{31st} priority:{L,M,H}`
    - tags: later, problem, work, project
- show all tasks: `task`
- complete task: `task {id} done`

## Keybinds <a name = "keybinds"></a>
- [I3](#keybinds_i3)
- [Nvim](#keybinds_nvim)
- [DBeaver](#keybinds_dbeaver)

### I3 <a name = "keybinds_i3"> </a>
- Find programs: `Win+d`
- Power settings: `Win+s`
- Monitor settings: `Win+o`
- Switch profile: `Win+i`
- Update/switch version: `Win+u`
- Switch workspace from monitor: `Win+shift+d`

### Nvim <a name = "keybinds_nvim"> </a>
- All commands are within nvim itself: `<space>h`

### DBeaver <a name = "keybinds_dbeaver"> </a>

#### In Table view
- View data in table: `Ctrl+d`

#### In Data view
- Go to table in overview, from inside: `ctrl + shift + ,`
- Go to definition of foreign key: `alt + space`
- Go back: `alt + arrow left`
- Go forward: `alt + arrow right`
- Select all row(s): `ctrl + alt + r`
- Select all column(s): `ctrl + alt + c`
- Show context menu for column: `ctrl + shift + alt + c`
- Go to filter: `ctrl + shift + alt + t`
- Go between data and value panel: `alt + v`
- Show row details: `tab`

## Language specific Documentation/Keybinds <a name = "language"></a>
- [PHP](documentation/PHP.md)

## NixOS Roles <a name = "nixos_roles"></a>
This configuration is organized into modular roles, each handling a specific aspect of the system:

- **alacritty**: Terminal emulator configuration
- **common**: Common system utilities (wget, curl, ripgrep, fzf, etc.)
- **docker**: Docker and docker-compose
- **git**: Git configuration with Meld as merge tool
- **gtk**: GTK theme configuration
- **i3**: i3 window manager with custom scripts
- **javascript**: Node.js, npm, and JavaScript development tools
- **neovim**: Neovim with LazyVim configuration
- **php**: PHP 8.3 with Composer and development tools
- **sql**: Database tools (PostgreSQL, MySQL, SQLite, DBeaver)
- **tmux**: Tmux terminal multiplexer
- **zsh**: Zsh shell with Oh My Zsh

Each role has:
- `roles/{role}/{role}.nix` - NixOS module defining packages and configuration
- `roles/{role}/configuration/` - Configuration files for the role

## Customization
You can customize the configuration by:
1. Editing individual role `.nix` files in `roles/{role}/{role}.nix`
2. Modifying configuration files in `roles/{role}/configuration/`
3. Editing `home.nix` to change which roles are included
4. Updating `flake.nix` to change Nix channels or add dependencies

After making changes, run `make switch` to apply them.

