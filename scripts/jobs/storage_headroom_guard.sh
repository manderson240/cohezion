#!/usr/bin/env bash
# Cohezion Local Storage Headroom Guard (Zero-Footprint Invariant)
# Alerts and enforces >150GB headroom on /home to prevent agent / kernel stalls.

set -euo pipefail

AVAIL_GB=$(df -BG /home | awk 'NR==2 {gsub("G",""); print $4}')
USE_PCT=$(df /home | awk 'NR==2 {gsub("%",""); print $5}')

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Storage check: ${AVAIL_GB}GB free (${USE_PCT}% used on /home)"

if [ "$USE_PCT" -ge 88 ] || [ "$AVAIL_GB" -lt 120 ]; then
    echo "[ALERT] Storage headroom critical: only ${AVAIL_GB}GB available (${USE_PCT}% used)!"
    # Alert via systemd notify / log
    exit 1
fi

echo "[OK] Storage headroom healthy (${AVAIL_GB}GB free >= 120GB threshold)."
