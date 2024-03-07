#!/usr/bin/env bash

names=()

while read i; do
    name=$(jq --raw-output '.name' <<< "$i")
    names+=($name)
done < <(jq -c '.[]' config.json)

printf -v namesString '%s,' "${names[@]}"
echo "What profile do you want?"
echo $namesString
read profile

echo $profile

while read i; do
	name=$(jq --raw-output '.name' <<< "$i")
	if [ "$profile" = "$name" ]; then
		task=$(jq --raw-output '.task' <<< "$i")
		nodeVersion=$(jq --raw-output '.node_version' <<< "$i")
		phpVersion=$(jq --raw-output '.php_version' <<< "$i")
	fi
done < <(jq -c '.[]' config.json)

if [ ! -v task ]; then
    echo "profile not found" >&2
    exit 1
fi

zsh -c "task context $task"
zsh -c "~/.dotfiles/roles/i3/files/scripts/Windows/Update/npm $nodeVersion"
zsh -c "~/.dotfiles/roles/i3/files/scripts/Windows/Update/php $phpVersion"

if ! zsh -c "ssh-add -l" &>/dev/null; then
	zsh -c "ssh-add"
fi

