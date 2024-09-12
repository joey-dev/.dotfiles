# TODO, remove before mering. do place in docs:
- change root password:  echo root:{{ users_root_info.password | quote }} | chpasswd


# My .Dotfiles

These are all my settings and program's I use. Written in Ansible for easy installation, and synchronization between different computers.

## Table of Contents
- [Getting Started](#getting_started)
- [Configure Program](#configure)
- [Create a new project](#project)
- [Configuration](#configuration)
- [Commands](#commands)
- [Keybinds](#keybinds)
- [Language specific Documentation/Keybinds](#language)
- [Testing](#testing)


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

To open the questions, run `make configure`

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
For some language's, you might need to do more. Please go to [Language specific Documentation/Keybinds](#language)

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

