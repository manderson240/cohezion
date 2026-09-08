#!/usr/bin/env bash
# scripts/check_wd_mybook.sh
# Diagnostic and Mount Script for WD-MyBook Network HDD on Linux.

set -euo pipefail

MOUNT_POINT="/mnt/wd_mybook"
TARGET_HOST="192.168.86.31"
TARGET_SHARE="public"

echo "=========================================================================="
echo "  WD-MyBook Network HDD Mount Utility"
echo "=========================================================================="

echo -e "\n[Step 1] Verifying Mount Point ($MOUNT_POINT)..."
if [ ! -d "$MOUNT_POINT" ]; then
    sudo mkdir -p "$MOUNT_POINT"
fi

echo -e "\n[Step 2] Mounting //$TARGET_HOST/$TARGET_SHARE to $MOUNT_POINT..."
sudo mount -t cifs "//$TARGET_HOST/$TARGET_SHARE" "$MOUNT_POINT" -o guest,uid=$(id -u),gid=$(id -g),iocharset=utf8,noperm

echo -e "\n[Step 3] Verifying Drive Contents..."
ls -la "$MOUNT_POINT"

echo -e "\n  ✓ SUCCESS! WD-MyBook mounted cleanly at $MOUNT_POINT!"
