#!/usr/bin/env bash


status=$(systemctl --user status polybar | grep "active (running)")

if [[ $status ]] 
then
  systemctl --user stop polybar
else
  systemctl --user restart polybar
fi
