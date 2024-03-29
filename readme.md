# My .Dotfiles

These are all my settings and program's I use. Written in Ansible for easy installation, and synchronization between different computers.

## Table of Contents
- [Getting Started](#getting_started)
- [Configure Program](#configure)
- [Create a new project](#project)
- [Commands](#commands)
- [Keybinds](#keybinds)
- [Language specific Documentation/Keybinds](#language)
- [Testing](#testing)
- [Extra's](#extras)


## Getting Started <a name = "getting_started"></a>
Currently only Ubuntu 20.04 is supporterd.

Run the following 2 commands in your terminal:
-   make install
-   make provision

If you have a new system, without i3. Logout, and login agin
If you already have set-up i3, Run the following shortcut's:
-   win + shift + r (anywhere)
-   alt + r (in the terminal)

## Configure Program <a name = "configure"></a>
Some programs require custom configuration, which might be hard to automate

- [Meld](#configure_meld)

### Meld <a name = "configure_meld"> </a>

1. nvim ~/.gitconfig
2. add the following lines:
```
[merge]
	tool = meld

[mergetool "meld"]
	cmd = meld "$LOCAL" "$MERGED" "$REMOTE" --output "$MERGED"
	keepBackup = false
```

## Create a new project <a name = "project"></a>
run `nvim`.
within neovin run: `:Project {root}` (example: Project ~/Code/ProjectName)

For some language's, you might need to do more. Please go to [Language specific Documentation/Keybinds](#language)


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
#### Git
- Open Git Status: `<leader>gs`
  - Add all files: `A`
  - Unstage file: `gu`
  - Add file: `ga`
  - Revert file: `gr`
  - Commit: `gc`
  - Push: `gp`
  - Commit and Push: `gg`
- Toggle git blane: `<leader>gb`
- Open git merge commit in browser: `<leader>go`

#### Project Tree (pf)
- Open Tree: `<leader>pf`
- Open Tree and focus on the current open file: `<leader>pcf`
- Open Tree with only open files: `<leader>pof`

  - Within Open Files (pof):
    - Delete Buffer: `bd`

  - Within Project Tree (pf):
    - Fuzzy Finder: `/`
    - Fuzzy Finder for Directories: `D`
    - Navigate Up: `<bs>`
    - Open Split: `S`
    - Open Vertical Split: `s`
    - Close Node: `C`
    - Close All Nodes: `z`
    - Add File or Directory: `a`
    - Add Directory: `A` (also accepts optional config.show_path option like "add")
    - Delete: `d`
    - Rename: `r`
    - Copy to Clipboard: `y`
    - Cut to Clipboard: `x`
    - Paste from Clipboard: `p`
    - Copy (text input for destination): `c` (also accepts optional config.show_path option like "add")
    - Move (text input for destination): `m` (also accepts optional config.show_path option like "add")

#### Project Management (pl)
- List all projects: `<leader>pl`

#### File Search
- Find text in all files in the current project: `<leader>fif`
- Find a file in the current project: `<leader>ff`
    - Within File Search (ff/fif):
        - prev item `ctrl + p`
        - next item `ctrl + n`
        - enter file `enter`
- Find and replace: `:%Subvert/find/replace/g`
    - example: `:%Subvert/facilit{y,ies}/building{,s}/g`
- Find structure in current files (ctag's): `<leader>fs`

#### Text manipulation
- Word to snake_case: `crs`
- Word to camelCase: `crc`
- Word to UPPER_CASE: `cru`
- Word to dash-case: `cr-`
- Word to dot.case: `cr.`

#### Task Management (tm)
- Find/Run all tasks in the current project: `<leader>tm`

#### Markdown Viewing
- View Markdown: `<leader>vm`
- Stop viewing Markdown: `<leader>vM`

#### Marked Files
- Set mark on file: `<leader>mf`
- Clear mark list: `<leader>mc`
- Remove mark from file: `<leader>mr`
- Show all marked files: `<leader>M`
- Go to next marked file: `<leader>me`
- Go to previous marked file: `<leader>mq`

#### Navigation
- Go back 1 file: `Alt + q`
- Go to next file: `Alt + e`
- Close currentl file: `Alt + w`

#### Split-screen
- Split window: `ctrl+w,ctrl+v`
- Split window horizantally: `ctrl+w,ctrl+s`
- Go to left window: `ctrl+w,ctrl+h`
- Go to right window: `ctrl+w,ctrl+l`

#### Pasting
- Past current yanked: `p`
- Past current yanked before carret: `P`
- Sycle through pasted: `<leader>n`
- Sycle through pasted back: `<leader>N`
- copy to clipboard: `ctrl + alt + c`
- paste from clipboard: `ctrl + shift + v`

#### Comments
- Toggle comment line: `gcc`
- Toggle comment line in visual mode: `gc`

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
- [VUE](documentation/Vue.md)

## Testing <a name = "testing"></a>
To test the new features/improvements in ansible, there are 2 things:
1. run it locally. This way we know it will work for upgrading
2. run it on Vagrant. This way we know it will work for a new machine

### Testing in Vagrant
The Password for the Vagrant machine is: `vagrant`
run:
-   make install-test
-   ssh-keygen -f "/home/{username}/.ssh/known_hosts" -R "[127.0.0.1]:2222"
-   make test
-   ssh-copy-id -p 2222 vagrant@127.0.0.1
-   make test-reload

to run it clean again:
-   make test-new
-   ssh-copy-id -p 2222 vagrant@127.0.0.1
-   make test-reload


## Extra's <a name = "extras"></a>
### remove need to for passphrase this boot sycle
-   ssh-add ~/.ssh/id_rsa
