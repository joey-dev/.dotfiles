# My .Dotfiles

These are all my settings and programs I use. Written in NixOS configuration for easy installation, and synchronization between different computers.

## Table of Contents
- [Getting Started](#getting_started)
- [Configuration](#configuration)
- [Keybinds](#keybinds)
- [Language specific Documentation/Keybinds](#language)

## Getting Started <a name = "getting_started"></a>
Currently NixOS is supported. Each laptop is a **host** in `hosts/` (`work`, `personal`).

The repo holds both the **NixOS system config** and the **Home Manager config**. NixOS runs on the stable release (`nixpkgs-stable`), Home Manager on `nixos-unstable`.

### Prerequisites
- NixOS installed on your system
- Connect to Wi-Fi: Run `nmtui` in the terminal to establish an internet connection.
- Install Git: Run `nix-shell -p git`

### Installation

1. Clone this repository:
```bash
git clone https://github.com/joey-dev/.dotfiles.git ~/.dotfiles
cd ~/.dotfiles
```

2. Make sure the host has its NixOS files, and that they are staged in git (flakes ignore untracked files). For a new laptop, see [hosts/personal/README.md](hosts/personal/README.md): copy `/etc/nixos/hardware-configuration.nix` into `hosts/<host>/` and add a small `configuration.nix`.

3. Run the bootstrap script with the host name. It asks for your Git name and email, then switches NixOS and Home Manager:
```bash
./bootstrap.sh work
```
Flakes don't need to be enabled first; the script passes the flag itself.

4. Reboot your system to allow LightDM to start cleanly and load your new i3 configuration.

### Available Commands
The host defaults to the machine's hostname. Override with `HOST=work`.

- **Apply Home Manager:** `make switch` (`nh home switch`, shows a diff of what changed)
- **Apply NixOS:** `make os` (`nh os switch`, asks for sudo)
- **Build without applying:** `make build`
- **Update inputs:** `make update` (`nix flake update`)
- **Check flake:** `make check` (Builds the configuration and runs the lint checks: nixfmt, statix, deadnix, shellcheck)
- **Format:** `make fmt` (Formats all `.nix` files)
- **Garbage collection:** runs automatically every week, removing generations older than 14 days

### New project from a template
`templates/php-symfony/flake.nix` is a placeholder until you paste your own project flake into it.

```bash
nix flake init -t ~/.dotfiles#php-symfony
echo "use flake" > .envrc && direnv allow
```

## Configuration <a name = "configuration"></a>
- [Neovim Snippets](#configuration_snippets)

### Neovim Snippets <a name = "configuration_snippets"></a>
To create new snippets go to the nvim/snippets directory.
The filename is: `fileType.snippets`.
If all the snippets from one filetype are also used in another filetype, use extends {fileType}.
    Example, the vue.snippets has as first line: `extends js`
A snippets looks like this:
```snippet
snippet {snippetWord}
    {codeHere}
```

In the code you can use `${1:name}`. This will be the first item your carot goes to when selecting the snippetWord.
It starts with number 1, and goes up. number 0 will be the last one.

example:
```snippet
snippet pubf
	public function ${1:name}(${2:params}): ${3:return}
	{
		${0:body}
	}
```

## Keybinds <a name = "keybinds"></a>
- [I3](#keybinds_i3)
- [Nvim](#keybinds_nvim)
- [DBeaver](#keybinds_dbeaver)

### I3 <a name = "keybinds_i3"> </a>
- Find programs: `Win+d`
- Power settings: `Win+p`
- Monitor layout (autorandr profiles): `Win+m`
- Switch workspace from monitor: `Win+shift+d`
- Network settings: `Win+n`
- Audio settings: `Win+a`
- File Explorer: `Win+e`

### Nvim <a name = "keybinds_nvim"> </a>
- All commands are within nvim itself: `<space>h`

### DBeaver <a name = "keybinds_dbeaver"> </a>

#### Settings
DBeaver keeps its settings in its own workspace, so they are not linked by Home Manager.
Import them once by hand: **File → Import → General → Preferences**, and pick `roles/common/configuration/DBeaver.epf`.

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

## Structure <a name = "nixos_roles"></a>

```
flake.nix               hosts, Home Manager and NixOS configs, lint checks
hosts/
  roles.nix             roles enabled on every laptop
  home.nix              Home Manager settings shared by every host
  common.nix            NixOS settings shared by every host
  work/                 configuration.nix + hardware-configuration.nix
  personal/             (NixOS files not added yet)
roles/<role>/
  <role>.nix            Home Manager part, with a `roles.<role>.enable` option
  system.nix            optional NixOS part (docker, i3, neovim, php)
  configuration/        config files for the role
templates/              `nix flake init -t` templates
```

### Roles
- **alacritty**: Terminal emulator configuration
- **claude**: Claude Code with settings
- **common**: Common utilities (wget, curl, fzf, bat, eza, ...), Chrome, LibreOffice, flameshot
- **cursor**: Cursor editor
- **docker**: Docker (NixOS part)
- **ghostty**: Ghostty terminal, used for the file manager
- **git**: Git configuration with Meld as merge tool
- **gtk**: GTK theme configuration
- **i3**: i3 window manager, auto-lock (xidlehook), autorandr, media and brightness keys, LightDM and backlight udev rules (NixOS part)
- **javascript**: Node.js, npm, and JavaScript development tools
- **neovim**: Neovim with LazyVim configuration, nix-ld for Mason (NixOS part)
- **php**: PHP with Composer and development tools, Xdebug firewall port (NixOS part)
- **polybar**: Status bar
- **sql**: Database tools (PostgreSQL, MySQL, SQLite, DBeaver)
- **ssh**: SSH agent; keys are added to it on first use. Private hosts go in `~/.ssh/config.local`
- **tmux**: Tmux terminal multiplexer
- **vscode**: VS Code
- **zsh**: Zsh shell with Oh My Zsh

## Customization
- **Add a role:** create `roles/<role>/<role>.nix` with an `enable` option (copy an existing role), then add it to `hosts/roles.nix`. Roles are picked up automatically from the `roles/` folders.
- **Different roles per host:** give the host its own list in `flake.nix` (`hosts.<host>.roles`).
- **System settings:** shared ones in `hosts/common.nix`, role-specific ones in `roles/<role>/system.nix`, laptop-specific ones in `hosts/<host>/configuration.nix`.

After making changes, run `make switch` (Home Manager) or `make os` (NixOS) to apply them.
