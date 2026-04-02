#!/usr/bin/env bash
# Health Check Cron — runs 4x daily (midnight, 6am, noon, 6pm)
# Runs validate_compound_loop.py and persists results to SurrealDB
set -euo pipefail

COHEZION_DIR="/home/mike-anderson/dev/cohezion"
LOG_DIR="$COHEZION_DIR/logs/cron"
LOG="$LOG_DIR/health_check_$(date +%Y%m%d_%H%M).log"

cd "$COHEZION_DIR"
echo "=== Health Check: $(date) ===" >> "$LOG"

# Run validation
RESULT=$(.venv/bin/python scripts/validate_compound_loop.py 2>&1 || true)
echo "$RESULT" >> "$LOG"

# Extract pass/fail counts
PASSED=$(echo "$RESULT" | grep -oP '\d+(?=/\d+ steps passed)' || echo "0")
TOTAL=$(echo "$RESULT" | grep -oP '(?<=/)(\d+)(?= steps passed)' || echo "0")
STATUS="OK"
if [ "$PASSED" != "$TOTAL" ]; then
  STATUS="DEGRADED"
fi

# Persist to SurrealDB
curl -s -X POST http://localhost:8001/sql \
  -H "Accept: application/json" \
  -H "surreal-ns: cohezion" \
  -H "surreal-db: cohezion" \
  -u "root:root" \
  -d "CREATE health_check SET passed = $PASSED, total = $TOTAL, status = '$STATUS', created = time::now();" \
  >> "$LOG" 2>&1 || true

echo "=== Result: $PASSED/$TOTAL ($STATUS) ===" >> "$LOG"

# Alert on regression
if [ "$STATUS" = "DEGRADED" ]; then
  echo "ALERT: Health check degraded — $PASSED/$TOTAL passing" | tee -a "$LOG"
fi

find "$LOG_DIR" -name "health_check_*.log" -mtime +30 -delete 2>/dev/null || true
