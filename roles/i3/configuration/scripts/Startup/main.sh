#!/usr/bin/env bash

CONFIG_FILE=$(eval echo '~/.dotfiles/roles/i3/files/scripts/Startup/config.json')

names=()

while read i; do
    name=$(jq --raw-output '.name' <<< "$i")
    names+=($name)
done < <(jq -c '.[]' $CONFIG_FILE)

if ! zsh -c "ssh-add -l" &>/dev/null; then
	zsh -c "ssh-add"
fi

printf -v namesString '%s,' "${names[@]}"
echo "What profile do you want?"
echo $namesString
read profile

while read i; do
	name=$(jq --raw-output '.name' <<< "$i")
	if [ "$profile" = "$name" ]; then
		task=$(jq --raw-output '.task' <<< "$i")
		nodeVersion=$(jq --raw-output '.node_version' <<< "$i")
		phpVersion=$(jq --raw-output '.php_version' <<< "$i")
	fi
done < <(jq -c '.[]' $CONFIG_FILE)

if [ ! -v task ]; then
    echo "profile not found" >&2
    exit 1
fi

zsh -c "task context $task"

echo "Update NPM and PHP version to current profile?"
echo "y/n"
read updateVersion

if [ "$updateVersion" = "y" ]; then
	zsh -c "~/.dotfiles/roles/i3/files/scripts/Windows/Update/npm $nodeVersion"
	zsh -c "~/.dotfiles/roles/i3/files/scripts/Windows/Update/php $phpVersion"
fi

echo "Update System?"
echo "y/n"
read updateSystem

if [ "$updateSystem" = "y" ]; then
	zsh -c "cd ~/.dotfiles && git checkout master"
	zsh -c "cd ~/.dotfiles && git pull"
	zsh -c "cd ~/.dotfiles && make provision"
fi

