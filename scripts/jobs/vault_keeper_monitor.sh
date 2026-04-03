#!/bin/bash
# Alert if vault-keeper hasn't run in >7 hours
# Created: 2026-04-02

set -euo pipefail

LOG="${HOME}/vaults/cohezion-vault/metabolism/vault-keeper.log"
ALERT_FILE="${HOME}/vaults/cohezion-vault/metabolism/.vault_keeper_alert"

# Check log file exists
if [ ! -f "$LOG" ]; then
    echo "CRITICAL: vault-keeper.log missing"
    exit 1
fi

# Find last run timestamp
LAST_RUN=$(grep "Vault Keeper Cycle started" "$LOG" 2>/dev/null | tail -1 | awk '{print $1 " " $2}')

if [ -z "$$LAST_RUN" ]; then
    echo "WARNING: No vault-keeper runs found in log"
    exit 1
fi

# Calculate hours since last run
LAST_EPOCH=$(date -d "$LAST_RUN" +%s 2>/dev/null || echo 0)
NOW_EPOCH=$(date +%s)
DIFF_HOURS=$(( (NOW_EPOCH - LAST_EPOCH) / 3600 ))

if [ $DIFF_HOURS -gt 7 ]; then
    echo "WARNING: vault-keeper last ran ${DIFF_HOURS}h ago (expected every 6h)"
    # Create alert marker file
    echo "Last run: $LAST_RUN" > "$ALERT_FILE"
    exit 1
fi

# Clear any existing alert
if [ -f "$ALERT_FILE" ]; then
    rm "$ALERT_FILE"
fi

echo "OK: vault-keeper ran ${DIFF_HOURS}h ago"
exit 0
