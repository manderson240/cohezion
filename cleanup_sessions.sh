#!/bin/bash

echo "🧹 Cleaning up orphaned remote sessions..."

# Stop Chrome Remote Desktop if it's running
sudo systemctl stop chrome-remote-desktop 2>/dev/null

# Terminate any lingering gnome-remote-desktop processes
pkill -u $USER gnome-remote-desktop 2>/dev/null

# Restart the local user session components (safely)
systemctl --user restart gnome-remote-desktop 2>/dev/null

echo "✅ Remote processes cleared. You should now be able to log in locally without conflict."
echo "Tip: Run 'loginctl terminate-user $USER' as a last resort if you are still locked out."
