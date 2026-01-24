#!/bin/bash

# Configuration
DESKTOP_WIDTH=2560
DESKTOP_HEIGHT=1440

PIXELBOOK_WIDTH=1920
PIXELBOOK_HEIGHT=1080

CURRENT_RES=$(xrandr --current | grep "*" | awk '{print $1}')

if [ "$CURRENT_RES" == "${DESKTOP_WIDTH}x${DESKTOP_HEIGHT}" ]; then
    echo "Switching to Pixelbook Mode (${PIXELBOOK_WIDTH}x${PIXELBOOK_HEIGHT})..."
    /usr/bin/python3 ~/dev/cohezion/gnome_resolution.py $PIXELBOOK_WIDTH $PIXELBOOK_HEIGHT
else
    echo "Switching to Desktop Mode (${DESKTOP_WIDTH}x${DESKTOP_HEIGHT})..."
    /usr/bin/python3 ~/dev/cohezion/gnome_resolution.py $DESKTOP_WIDTH $DESKTOP_HEIGHT
fi
