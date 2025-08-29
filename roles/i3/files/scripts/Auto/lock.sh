#!/bin/bash

ALL_DISPLAYS=$(xrandr | awk '/ connected/ {print $1}')

xidlehook \
  --not-when-fullscreen \
  --timer 120 \
    "$(for display in $ALL_DISPLAYS; do echo "xrandr --output $display --brightness .1;"; done)" \
    "$(for display in $ALL_DISPLAYS; do echo "xrandr --output $display --brightness 1;"; done)" \
  --timer 10 \
    "$(for display in $ALL_DISPLAYS; do echo "xrandr --output $display --brightness 1;"; done; echo 'i3lock -c 000000')" \
    ''
