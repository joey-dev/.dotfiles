# My .Dotfiles

These are all my settings and programs I use. Written in NixOS configuration for easy installation, and synchronization between different computers.

## Table of Contents
- [Getting Started](#getting_started)
- [Configuration](#configuration)
- [Keybinds](#keybinds)
- [Language specific Documentation/Keybinds](#language)

## Getting Started <a name = "getting_started"></a>
Currently NixOS is supported.

### Prerequisites
- NixOS installed on your system
- Connect to Wi-Fi: Run `nmtui` in the terminal to establish an internet connection.
- Install Git: Run `nix-shell -p git`
- Install a basic editor: Run `nix-shell -p vim` (to make any temporary edits to `configuration.nix` before building).

### System Configuration (Pre-Installation)
Before installing these dotfiles, your base NixOS system needs to be configured to support the graphical environment, your user permissions, and the Docker daemon. 

Add the following to your `/etc/nixos/configuration.nix`:

```nix
  # Enable the X11 windowing system
  services.xserver = {
    enable = true;
    
    # Enable the LightDM Display Manager
    displayManager.lightdm.enable = true;
    
    # Defer to Home Manager for the window manager
    desktopManager.runXdgAutostartIfNone = true;
    
    # System-level fallback
    windowManager.i3.enable = true; 
  };

  # Enable Nix-LD (Required for Neovim LSPs and Mason downloaded binaries)
  programs.nix-ld.enable = true;

  # Enable Docker system-wide
  virtualisation.docker.enable = true;

  # Define your user account and add to the docker group
  users.users.joey = {
    isNormalUser = true;
    description = "Joey";
    extraGroups = [ "networkmanager" "wheel" "docker" ]; 
  };

  nix.settings.experimental-features = [ "nix-command" "flakes" ];
```

Apply the system changes by running:
```bash
sudo nixos-rebuild switch
```

### Installation

1. Clone this repository:
```bash
git clone [https://github.com/joey-dev/.dotfiles.git](https://github.com/joey-dev/.dotfiles.git) ~/.dotfiles
cd ~/.dotfiles
```

2. Run the automated bootstrap script. This will prompt you for your Git credentials, securely create your local config, and execute the first Home Manager build:
```bash
./bootstrap.sh
```

3. Reboot your system to allow LightDM to start cleanly and load your new i3 configuration.

### Available Commands
- **Apply configuration:** `home-manager switch --flake .#joey` (Run this after making changes to any `.nix` file)
- **Update inputs:** `nix flake update` (Bumps your packages to the latest versions)
- **Check flake:** `nix flake check` (Validates the configuration locally)
- **Garbage collection:** `nix-collect-garbage -d` (Frees up disk space by removing old generations)

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
- Monitor settings: `Win+m`
- Switch workspace from monitor: `Win+shift+d`
- Network settings: `Win+n`
- Audio settings: `Win+a`
- File Explorer: `Win+e`

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

After making changes, run `home-manager switch --flake .#joey` to apply them.
