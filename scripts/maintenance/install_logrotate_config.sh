#!/usr/bin/env bash
# Install logrotate rsyslog config
# Usage: sudo ./install_logrotate_config.sh [--check]

set -euo pipefail

# Configuration
SOURCE_CONFIG="systemd/logrotate-rsyslog.conf"
DEST_CONFIG="/etc/logrotate.d/rsyslog"
BACKUP_SUFFIX=".pre-cohezion-$(date +%Y%m%d)"

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

# Verify logrotate config syntax
verify_config() {
    info "Verifying logrotate configuration syntax..."

    if logrotate -d "$DEST_CONFIG" &>/dev/null; then
        info "✅ Configuration syntax is valid"
        return 0
    else
        warn "Configuration syntax check failed"
        return 1
    fi
}

# Check-only mode
if [[ "$CHECK_ONLY" == "true" ]]; then
    echo "Logrotate Configuration Status"
    echo "==============================="
    echo ""
    echo "Source:      $SOURCE_CONFIG"
    echo "Destination: $DEST_CONFIG"
    echo ""

    STATUS=$(check_installation)

    case "$STATUS" in
        not_installed)
            warn "Status: NOT INSTALLED (or system default)"
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
            if verify_config 2>/dev/null; then
                exit 0
            else
                warn "Config file is up to date but syntax check failed"
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

# Backup existing config if it exists and is different
if [[ -f "$DEST_CONFIG" ]]; then
    DEST_MD5=$(sha256sum "$DEST_CONFIG" 2>/dev/null | cut -d' ' -f1)
    SOURCE_MD5=$(sha256sum "$SOURCE_CONFIG" | cut -d' ' -f1)

    if [[ "$DEST_MD5" != "$SOURCE_MD5" ]]; then
        BACKUP_FILE="${DEST_CONFIG}${BACKUP_SUFFIX}"
        if [[ ! -f "$BACKUP_FILE" ]]; then
            info "Creating backup: $BACKUP_FILE"
            cp "$DEST_CONFIG" "$BACKUP_FILE"
        else
            info "Backup already exists: $BACKUP_FILE"
        fi
    fi
fi

case "$STATUS" in
    not_installed)
        info "Installing logrotate config for the first time..."
        ;;
    outdated)
        warn "Config file has changed, updating..."
        ;;
    up_to_date)
        info "Config is already up to date"
        if verify_config 2>/dev/null; then
            info "Nothing to do - config is installed and valid"
            exit 0
        else
            warn "Config syntax check failed, reinstalling..."
        fi
        ;;
esac

# Copy config file
info "Copying $SOURCE_CONFIG to $DEST_CONFIG..."
cp "$SOURCE_CONFIG" "$DEST_CONFIG"
chmod 644 "$DEST_CONFIG"

# Verify installation
if verify_config; then
    info "✅ Installation complete and verified"

    echo ""
    info "Rotation policy summary:"
    echo "  - Rotation schedule: weekly OR when file exceeds 100MB"
    echo "  - Rotations kept: 8 (compressed)"
    echo "  - Compression: enabled (delayed by 1 cycle)"

    echo ""
    info "Current syslog files:"
    ls -lh /var/log/syslog* 2>/dev/null | head -10 || true

    echo ""
    warn "To force an immediate rotation (if needed):"
    echo "  sudo logrotate -f /etc/logrotate.d/rsyslog"

    exit 0
else
    error "Installation completed but verification failed"
    error "Check 'sudo logrotate -d /etc/logrotate.d/rsyslog' for errors"
    exit 1
fi
