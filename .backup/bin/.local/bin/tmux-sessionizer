#!/usr/bin/env bash

if [[ $# -eq 1 ]]; then
    folders=$1
else
    folders=$(find / /home /usr ~ ~/Code/Learning ~/Code/Projects ~/Code/Test ~/Code/Work -mindepth 1 -maxdepth 1 -type d)
	alphabet=( "a" "b" "c" "d" "e" "f" "g" "h" "i" "j" "k" "l" "m" "n" "o" "p" "q" "r" "s" "t" "u" "v" "w" "x" "y" "z")

	items=("${folders[@]}" "${alphabet[@]}")

	selected=$(echo "${items[@]}" | tr ' ' '\n' | fzf)
fi


if [[ -z $selected ]]; then
    exit 0
fi

if [ ${#selected} -eq 1 ]; then
	selected_name=$selected
	selected="/"
else
	selected_name=$(basename "$selected" | tr . _)
fi

tmux_running=$(pgrep tmux)

if [[ -z $TMUX ]] && [[ -z $tmux_running ]]; then
    tmux new-session -s $selected_name -c $selected
    exit 0
fi

if ! tmux has-session -t=$selected_name 2> /dev/null; then
    tmux new-session -ds $selected_name -c $selected
fi

tmux switch-client -t $selected_name



