#!/bin/sh
# Process Analyzer with Log Rotation
# Per SYSTEM_MONITORING_PRIME: Keep 1 hour of data (360 entries @ 10s intervals)
# Model: claude-opus-4 + local SLM swarm | Agent: Antigravity | Task: IDE Crash Prevention

LOG_DIR="/home/mike-anderson/dev/cohezion/src/diagnostics"
USAGE_LOG="${LOG_DIR}/process_usage.log"
MAX_LINES=3600  # 360 snapshots * ~10 lines each

rotate_log() {
  local log_file="$1"
  local max="$2"
  if [ -f "$log_file" ]; then
    tail -n "$max" "$log_file" > "${log_file}.tmp" && mv "${log_file}.tmp" "$log_file"
  fi
}

while true; do
  # Timestamp for correlation
  echo "=== $(date -Iseconds) ===" >> "$USAGE_LOG"
  ps -eo pid,user,%cpu,%mem,rss,args --sort=-%mem | head -21 >> "$USAGE_LOG"
  
  # Rotate to keep bounded
  rotate_log "$USAGE_LOG" $MAX_LINES
  
  sleep 10
done
