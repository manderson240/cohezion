#!/usr/bin/env bash
# Cohezion Simulation Cron Runner
# Runs overnight_driver.py with proper logging to SurrealDB
# Designed for systemd timer or crontab execution

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$PROJECT_DIR/logs"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="$LOG_DIR/simulation_$TIMESTAMP.log"

# Ensure log directory exists
mkdir -p "$LOG_DIR"

# Activate virtual environment
cd "$PROJECT_DIR"

echo "=== Cohezion Simulation Run ===" | tee -a "$LOG_FILE"
echo "Timestamp: $(date -Iseconds)" | tee -a "$LOG_FILE"
echo "Working Directory: $PROJECT_DIR" | tee -a "$LOG_FILE"

# Check SurrealDB is running
if ! curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "ERROR: SurrealDB not running. Starting..." | tee -a "$LOG_FILE"
    # Attempt to start (assumes systemd service exists)
    sudo systemctl start surrealdb 2>/dev/null || echo "Could not start SurrealDB" | tee -a "$LOG_FILE"
    sleep 2
fi

# Check Ollama is running
if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "ERROR: Ollama not running. Starting..." | tee -a "$LOG_FILE"
    ollama serve &
    sleep 5
fi

# Run simulation with timeout (4 hours max)
echo "Starting simulation driver..." | tee -a "$LOG_FILE"
timeout 14400 uv run python overnight_driver.py --duration 4h 2>&1 | tee -a "$LOG_FILE"
EXIT_CODE=$?

# Log completion
echo "=== Simulation Complete ===" | tee -a "$LOG_FILE"
echo "Exit Code: $EXIT_CODE" | tee -a "$LOG_FILE"
echo "Finished: $(date -Iseconds)" | tee -a "$LOG_FILE"

# Cleanup old logs (keep last 30 days)
find "$LOG_DIR" -name "simulation_*.log" -mtime +30 -delete 2>/dev/null || true

exit $EXIT_CODE
