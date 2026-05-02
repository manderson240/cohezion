#!/usr/bin/env bash
# SessionStart hook: Check for Entire CLI updates and auto-install.
# Non-blocking: always exits 0.

if ! command -v entire &>/dev/null; then
    exit 0  # Entire not installed, skip
fi

UPDATE_CHECK=$(entire version 2>&1)
if echo "$UPDATE_CHECK" | grep -qi "newer version"; then
    echo "[entire-auto-update] Updating Entire CLI..."
    curl -fsSL https://entire.io/install.sh | bash 2>/dev/null
    NEW_VERSION=$(entire version 2>/dev/null | head -1)
    echo "[entire-auto-update] Updated to $NEW_VERSION"
else
    VERSION=$(echo "$UPDATE_CHECK" | head -1)
    echo "[entire-auto-update] $VERSION (up to date)"
fi

exit 0
