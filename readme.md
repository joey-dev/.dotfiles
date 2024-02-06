# My .Dotfiles

These are all my settings and program's I use. Written in Ansible for easy installation, and synchronization between different computers.

## Table of Contents
- [Getting Started](#getting_started)
- [Create a new project](#project)
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

## Create a new project <a name = "project"></a>
run `nvim`.
within neovin run: `:Project {root}` (example: Project ~/Code/ProjectName)

For some language's, you might need to do more. Please go to [Language specific Documentation/Keybinds](#language)


## Commands <a name = "commands"></a>
- [Todo List](#commands_todo_list)

### Todo List <a name = "commands_todo_list"</a>
- switch context (work, project): `task context work`
- add task: `task add {description of the task} +{tag} due:{31st} priority:{L,M,H}`
    - tags: later, problem, work, project
- show all tasks: `task`
- complete task: `task {id} done`

## Keybinds <a name = "keybinds"></a>
- [Nvim](#keybinds_nvim)

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
