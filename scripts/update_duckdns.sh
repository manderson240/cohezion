#!/usr/bin/env bash
# DuckDNS Dynamic IP Updater for cohezion.duckdns.org
# Add to crontab: */5 * * * * /path/to/update_duckdns.sh

set -euo pipefail

DOMAIN="cohezion"
TOKEN="${DUCKDNS_TOKEN:-}"
LOG_FILE="/home/mike-anderson/dev/cohezion/logs/duckdns.log"

if [ -z "$TOKEN" ]; then
    source /home/mike-anderson/dev/cohezion/.env 2>/dev/null || true
    TOKEN="${DUCKDNS_TOKEN:-}"
fi

if [ -z "$TOKEN" ]; then
    echo "$(date -Iseconds) ERROR: DUCKDNS_TOKEN not set" >> "$LOG_FILE"
    exit 1
fi

# Update DuckDNS
RESULT=$(curl -s "https://www.duckdns.org/update?domains=$DOMAIN&token=$TOKEN&ip=")

echo "$(date -Iseconds) DuckDNS update: $RESULT" >> "$LOG_FILE"

if [ "$RESULT" = "OK" ]; then
    exit 0
else
    echo "$(date -Iseconds) ERROR: DuckDNS update failed" >> "$LOG_FILE"
    exit 1
fi
