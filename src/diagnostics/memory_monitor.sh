#!/bin/sh
# Memory Monitor with Log Rotation
# Per SYSTEM_MONITORING_PRIME: Keep 1 hour of data (720 entries @ 5s intervals)
# Model: claude-opus-4 + local SLM swarm | Agent: Antigravity | Task: IDE Crash Prevention

LOG_DIR="/home/mike-anderson/dev/cohezion/src/diagnostics"
MEM_LOG="${LOG_DIR}/memory_usage.log"
PROC_LOG="${LOG_DIR}/process_list.log"
MAX_LINES=720

rotate_log() {
  local log_file="$1"
  local max="$2"
  if [ -f "$log_file" ]; then
    tail -n "$max" "$log_file" > "${log_file}.tmp" && mv "${log_file}.tmp" "$log_file"
  fi
}

while true; do
  # Timestamp for correlation
  echo "=== $(date -Iseconds) ===" >> "$MEM_LOG"
  free -h >> "$MEM_LOG"
  
  # Top 20 memory consumers with timestamp
  echo "=== $(date -Iseconds) ===" >> "$PROC_LOG"
  ps aux --sort=-%mem | head -21 >> "$PROC_LOG"
  
  # Rotate logs to keep bounded size
  rotate_log "$MEM_LOG" $MAX_LINES
  rotate_log "$PROC_LOG" $((MAX_LINES * 3))  # ~2100 lines for process list
  
  sleep 5
done
