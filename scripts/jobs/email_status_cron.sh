#!/usr/bin/env bash
# Email Status Notification — hourly substantial updates to manderson240@gmail.com
# Generates status report, sends via Python smtplib or writes to log
set -euo pipefail

COHEZION_DIR="/home/mike-anderson/dev/cohezion"
LOG_DIR="$COHEZION_DIR/logs/cron"
LOG="$LOG_DIR/email_status_$(date +%Y%m%d_%H%M).log"
REPORT_DIR="$COHEZION_DIR/logs/status_reports"
LOCK="/tmp/cohezion_email_status.lock"

mkdir -p "$LOG_DIR" "$REPORT_DIR"

exec 200>"$LOCK"
flock -n 200 || { echo "Already running" >> "$LOG"; exit 0; }

cd "$COHEZION_DIR"

echo "=== Status Report: $(date) ===" >> "$LOG"

# Generate and send report
.venv/bin/python scripts/generate_status_report.py \
    --output "$REPORT_DIR/status_$(date +%Y%m%d_%H%M).txt" \
    --email manderson240@gmail.com \
    >> "$LOG" 2>&1 || true

echo "=== Complete: $(date) ===" >> "$LOG"

# Rotate old reports (keep 48 hours)
find "$REPORT_DIR" -name "status_*.txt" -mtime +2 -delete 2>/dev/null || true
find "$LOG_DIR" -name "email_status_*.log" -mtime +7 -delete 2>/dev/null || true
