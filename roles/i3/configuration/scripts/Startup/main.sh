#!/usr/bin/env bash

CONFIG_FILE=$(eval echo '~/.dotfiles/roles/i3/configuration/scripts/Startup/config.json')

names=()

while read i; do
    name=$(jq --raw-output '.name' <<< "$i")
    names+=($name)
done < <(jq -c '.[]' $CONFIG_FILE)

if ! zsh -c "ssh-add -l" &>/dev/null; then
	zsh -c "ssh-add"
fi

