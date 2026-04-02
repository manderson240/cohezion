#!/usr/bin/env bash
# Kernel Submission Cron — runs every 30 min during Luma competition
# Tests current best variant → benchmarks → submits if improved
set -euo pipefail

COHEZION_DIR="/home/mike-anderson/dev/cohezion"
LOG_DIR="$COHEZION_DIR/logs/cron"
LOG="$LOG_DIR/kernel_submit_$(date +%Y%m%d_%H%M).log"
LOCK="/tmp/cohezion_kernel_submit.lock"

exec 200>"$LOCK"
flock -n 200 || { echo "Already running" >> "$LOG"; exit 0; }

cd "$COHEZION_DIR"
echo "=== Kernel Submission Cycle: $(date) ===" >> "$LOG"

# Check all 3 kernels and report status
.venv/bin/python scripts/compound_kernel_cycle.py --kernel all --history >> "$LOG" 2>&1 || true

# Persist health check
curl -s -X POST http://localhost:8001/sql \
  -H "Accept: application/json" \
  -H "surreal-ns: cohezion" \
  -H "surreal-db: cohezion" \
  -u "root:root" \
  -d "CREATE kernel_health SET date = '$(date +%Y-%m-%d)', time = '$(date +%H:%M)', status = 'checked', created = time::now();" \
  >> "$LOG" 2>&1 || true

echo "=== Complete: $(date) ===" >> "$LOG"

find "$LOG_DIR" -name "kernel_submit_*.log" -mtime +7 -delete 2>/dev/null || true
