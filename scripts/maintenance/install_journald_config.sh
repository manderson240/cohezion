#!/usr/bin/env bash
# Install journald retention config
# Usage: sudo ./install_journald_config.sh [--check]

set -euo pipefail

# Configuration
SOURCE_CONFIG="systemd/journald-cohezion.conf"
DEST_CONFIG="/etc/systemd/journald.conf.d/cohezion.conf"
DEST_DIR="/etc/systemd/journald.conf.d"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Parse arguments
CHECK_ONLY=false
if [[ ${1:-} == "--check" ]]; then
    CHECK_ONLY=true
fi

# Function to print colored output
info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if source config exists
if [[ ! -f "$SOURCE_CONFIG" ]]; then
    error "Source config not found: $SOURCE_CONFIG"
    error "Run this script from the repository root"
    exit 1
fi

# Check current installation status
check_installation() {
    if [[ ! -f "$DEST_CONFIG" ]]; then
        echo "not_installed"
        return
    fi

    # Compare checksums
    SOURCE_MD5=$(sha256sum "$SOURCE_CONFIG" | cut -d' ' -f1)
    DEST_MD5=$(sha256sum "$DEST_CONFIG" 2>/dev/null | cut -d' ' -f1)

    if [[ "$SOURCE_MD5" == "$DEST_MD5" ]]; then
        echo "up_to_date"
    else
        echo "outdated"
    fi
}

# Verify journald is using our settings
verify_settings() {
    info "Verifying journald configuration..."

    # Check if our config is loaded
    if systemd-analyze cat-config systemd/journald.conf 2>/dev/null | grep -q "SystemMaxUse=2G"; then
        info "✅ SystemMaxUse=2G is active"
    else
        warn "SystemMaxUse setting not found in active config"
        return 1
    fi

    if systemd-analyze cat-config systemd/journald.conf 2>/dev/null | grep -q "MaxRetentionSec=30day"; then
        info "✅ MaxRetentionSec=30day is active"
    else
        warn "MaxRetentionSec setting not found in active config"
        return 1
    fi

    if systemd-analyze cat-config systemd/journald.conf 2>/dev/null | grep -q "RateLimitBurst=1000"; then
        info "✅ RateLimitBurst=1000 is active"
    else
        warn "RateLimitBurst setting not found in active config"
        return 1
    fi

    info "All settings verified successfully"
    return 0
}

# Check-only mode
if [[ "$CHECK_ONLY" == "true" ]]; then
    echo "Journald Configuration Status"
    echo "=============================="
    echo ""
    echo "Source:      $SOURCE_CONFIG"
    echo "Destination: $DEST_CONFIG"
    echo ""

    STATUS=$(check_installation)

    case "$STATUS" in
        not_installed)
            warn "Status: NOT INSTALLED"
            echo ""
            echo "To install, run:"
            echo "  sudo $0"
            exit 1
            ;;
        outdated)
            warn "Status: OUTDATED (config has changed)"
            echo ""
            echo "Source checksum:      $(sha256sum "$SOURCE_CONFIG" | cut -d' ' -f1)"
            echo "Installed checksum:   $(sha256sum "$DEST_CONFIG" | cut -d' ' -f1)"
            echo ""
            echo "To update, run:"
            echo "  sudo $0"
            exit 1
            ;;
        up_to_date)
            info "Status: UP TO DATE"
            echo ""
            if verify_settings 2>/dev/null; then
                exit 0
            else
                warn "Config file is up to date but settings not active"
                echo "Try: sudo systemctl restart systemd-journald"
                exit 1
            fi
            ;;
    esac
fi

# Installation mode - require sudo
if [[ $EUID -ne 0 ]]; then
    error "This script must be run with sudo for installation"
    echo ""
    echo "Usage:"
    echo "  $0 --check           # Check status (no sudo required)"
    echo "  sudo $0              # Install/update config"
    exit 1
fi

# Check current status
STATUS=$(check_installation)

info "Current status: $STATUS"

case "$STATUS" in
    not_installed)
        info "Installing journald config for the first time..."
        ;;
    outdated)
        warn "Config file has changed, updating..."
        ;;
    up_to_date)
        info "Config is already up to date"
        if verify_settings 2>/dev/null; then
            info "Nothing to do - config is installed and active"
            exit 0
        else
            info "Config file is up to date but not active, restarting journald..."
        fi
        ;;
esac

# Create destination directory if it doesn't exist
if [[ ! -d "$DEST_DIR" ]]; then
    info "Creating $DEST_DIR..."
    mkdir -p "$DEST_DIR"
fi

# Copy config file
info "Copying $SOURCE_CONFIG to $DEST_CONFIG..."
cp "$SOURCE_CONFIG" "$DEST_CONFIG"
chmod 644 "$DEST_CONFIG"

# Restart systemd-journald to apply changes
info "Restarting systemd-journald..."
systemctl restart systemd-journald

# Wait a moment for the restart to complete
sleep 2

# Verify installation
if verify_settings; then
    info "✅ Installation complete and verified"

    # Show current journal disk usage
    echo ""
    info "Current journal disk usage:"
    journalctl --disk-usage 2>/dev/null || true

    echo ""
    info "Retention policy summary:"
    echo "  - Max total disk usage: 2GB"
    echo "  - Max retention period: 30 days"
    echo "  - Rate limit: 1000 messages/30s"

    exit 0
else
    error "Installation completed but verification failed"
    error "Check 'journalctl -u systemd-journald' for errors"
    exit 1
fi
