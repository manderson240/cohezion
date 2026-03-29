#!/usr/bin/env bash
# Runs all *_hourly.py job scripts with logging and timeouts.
# Called by systemd/cohezion-jobs.timer or manually.
set -euo pipefail

cd "$(dirname "$0")/.."
LOG_DIR="${HOME}/.local/share/cohezion/job-logs"
mkdir -p "$LOG_DIR"
TIMESTAMP=$(date +%Y%m%d_%H%M)
FAILURES=0

for job in scripts/jobs/*_hourly.py; do
    [ -f "$job" ] || continue
    JOB_NAME=$(basename "$job" .py)
    echo "[run_jobs] Starting $JOB_NAME at $(date +%H:%M:%S)..."
    if timeout 600 uv run python "$job" > "$LOG_DIR/${JOB_NAME}_${TIMESTAMP}.log" 2>&1; then
        echo "[run_jobs] $JOB_NAME completed."
    else
        echo "[run_jobs] $JOB_NAME FAILED (exit $?)" | tee -a "$LOG_DIR/failures_${TIMESTAMP}.log"
        FAILURES=$((FAILURES + 1))
    fi
done

echo "[run_jobs] All jobs complete. Failures: $FAILURES"

# Clean up logs older than 7 days
find "$LOG_DIR" -name "*.log" -mtime +7 -delete 2>/dev/null || true
