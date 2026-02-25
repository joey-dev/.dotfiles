#!/usr/bin/env bash
# Manage logout with rofi
option=`echo -e "lock screen\nsuspend\nlogout\nreboot\npoweroff\nKill user $USER" | rofi -width 600 -dmenu -p power`
case $option in
    'lock screen')
        i3lock -c 000000
        ;;
    suspend)
        sudo systemctl suspend
        ;;
    logout)
        i3-nagbar -t warning -m 'Are you sure you  want to exit i3? This will end your X session.' -b 'Yes, exit i3' 'i3-msg exit'
        ;;
    reboot)
        systemctl reboot
        ;;
    poweroff)
        systemctl poweroff
        ;;
    'kill user $USER')
        loginctl kill-user $USER
        ;;
esac
