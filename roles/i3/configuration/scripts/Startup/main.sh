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
	fi
done < <(jq -c '.[]' $CONFIG_FILE)

if [ ! -v task ]; then
    echo "profile not found" >&2
    exit 1
fi

zsh -c "task context $task"

echo "Update System?"
echo "y/n"
read updateSystem

if [ "$updateSystem" = "y" ]; then
	zsh -c "cd ~/.dotfiles && nix run github:nix-community/home-manager -- switch --flake .#joey"
fi

