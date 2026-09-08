#!/usr/bin/env bash
set -euo pipefail

# Sovereign Overnight Autopoiesis Daemon Launcher
# Enforces fleet preflight, starts background evolution loop, and logs output.

LOG_FILE="/tmp/cohezion_overnight_autopoiesis.log"
PID_FILE="/tmp/cohezion_overnight_autopoiesis.pid"

echo "=== Pre-flight Fleet Health Check ==="
bash scripts/preflight_fleet.sh

# Check if previous daemon is running
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    if ps -p "$OLD_PID" > /dev/null 2>&1; then
        echo "⚠️ An existing autopoiesis daemon is already running (PID: $OLD_PID)."
        echo "Tailing log: $LOG_FILE"
        exit 0
    fi
fi

echo "=== Launching Overnight Autopoiesis Daemon ==="
echo "Started at: $(date -Iseconds)"

PYTHONPATH=src nohup .venv/bin/python -u scripts/ops/autonomous_overnight_autopoiesis_daemon.py >> "$LOG_FILE" 2>&1 &
DAEMON_PID=$!

echo "$DAEMON_PID" > "$PID_FILE"
echo "✅ Daemon launched successfully with PID $DAEMON_PID."
echo "Logs streaming to: $LOG_FILE"
echo "To monitor: tail -f $LOG_FILE"
