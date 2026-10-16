#!/usr/bin/env bash
# Pick a saved autorandr profile with rofi
profile=$(autorandr --list | rofi -dmenu -p monitor) || exit 0
autorandr --load "$profile"
