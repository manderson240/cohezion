#!/usr/bin/env bash
# scripts/check_wd_mybook.sh
# Diagnostic and Fallback Mount Script for WD-MyBook Network HDD on Linux.

set -euo pipefail

MOUNT_POINT="/mnt/wd_mybook"
LOG_FILE="/tmp/wd_mybook_mount.log"

echo "=========================================================================="
echo "  WD-MyBook Network HDD Diagnostic & Fallback Mount Utility"
echo "=========================================================================="

# Step 1: Discover Local WD-MyBook IP or Hostname
echo -e "\n[Step 1] Discovering WD-MyBook Network Host..."
TARGET_IP=""

# Try pinging known local hostnames
for host in "wdmybook.local" "mybook.local" "wd-mybook.local" "WDMyBook"; do
    if ping -c 1 -W 1 "$host" &>/dev/null; then
        TARGET_IP=$(getent hosts "$host" 2>/dev/null | awk '{print $1}' || true)
        if [ -n "$TARGET_IP" ]; then
            echo "  ✓ Found host $host at IP: $TARGET_IP"
            break
        fi
    fi
done

# If mDNS failed, check /proc/net/arp or ip neighbor
if [ -z "$TARGET_IP" ]; then
    echo "  · Checking ARP table (/proc/net/arp)..."
    TARGET_IP=$(awk 'NR>1 {print $1}' /proc/net/arp 2>/dev/null | head -n 1 || true)
fi

if [ -z "$TARGET_IP" ]; then
    echo "  ⚠️ Warning: Could not automatically resolve WD-MyBook IP. Defaulting to 192.168.1.100."
    TARGET_IP="192.168.1.100"
fi

echo "  Target IP: $TARGET_IP"

# Step 2: Test Port Connectivity
echo -e "\n[Step 2] Probing SMB ports (445 / 139)..."
if nc -z -w 2 "$TARGET_IP" 445 2>/dev/null; then
    echo "  ✓ Port 445 (SMB) is OPEN."
elif nc -z -w 2 "$TARGET_IP" 139 2>/dev/null; then
    echo "  ✓ Port 139 (NetBIOS SMB) is OPEN."
else
    echo "  ⚠️ Warning: Ports 445 and 139 on $TARGET_IP did not respond to TCP probe."
fi

# Step 3: Generated Mount Commands & /etc/fstab Configuration
echo -e "\n[Step 3] Generated Mount Commands & /etc/fstab Configuration"
echo "  To mount the drive manually, create the mount directory and run:"
echo "  ------------------------------------------------------------------------"
echo "  sudo mkdir -p $MOUNT_POINT"
echo "  sudo mount -t cifs //$TARGET_IP/Public $MOUNT_POINT -o vers=2.0,guest,uid=\$(id -u),gid=\$(id -g),iocharset=utf8,noperm"
echo "  ------------------------------------------------------------------------"
echo ""
echo "  If the drive uses legacy SMB1/NT1 (Kernel 5.15+ fallback):"
echo "  ------------------------------------------------------------------------"
echo "  sudo mount -t cifs //$TARGET_IP/Public $MOUNT_POINT -o vers=1.0,sec=ntlmssp,guest,uid=\$(id -u),gid=\$(id -g),iocharset=utf8,noperm"
echo "  ------------------------------------------------------------------------"
echo ""
echo "  To enable automatic mounting on boot, add this line to /etc/fstab:"
echo "  ------------------------------------------------------------------------"
echo "  //$TARGET_IP/Public $MOUNT_POINT cifs vers=2.0,guest,uid=1000,gid=1000,iocharset=utf8,noperm 0 0"
echo "  ------------------------------------------------------------------------"

echo -e "\nDiagnostics complete."
