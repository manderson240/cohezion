#!/usr/bin/env bash
# Headless maintenance cycle for Cohezion codebase and vault.
# Runs /maintain skill autonomously with restricted tools and turn limits.
#
# Usage:
#   ./scripts/headless/maintain.sh [count]
#
# Arguments:
#   count  - Max issues to fix (default: 10)
#
# Output is logged to ~/.cohezion-engine/logs/maintain-<date>.log

set -euo pipefail

COUNT="${1:-10}"
LOG_DIR="${HOME}/.cohezion-engine/logs"
LOG_FILE="${LOG_DIR}/maintain-$(date +%Y%m%d-%H%M%S).log"

if [ "${1:-}" = "--help" ] || [ "${1:-}" = "-h" ]; then
    echo "Usage: $0 [count]"
    echo ""
    echo "Run an autonomous maintenance cycle on the Cohezion codebase."
    echo ""
    echo "Arguments:"
    echo "  count   Max issues to fix (default: 10)"
    echo ""
    echo "Logs written to: ${LOG_DIR}/maintain-<timestamp>.log"
    exit 0
fi

mkdir -p "$LOG_DIR"

echo "[maintain] Starting maintenance cycle (max $COUNT issues)..."
echo "[maintain] Log: $LOG_FILE"

claude -p "/maintain $COUNT" \
    --allowedTools "Read,Edit,Write,Bash,Grep,Glob" \
    --max-turns 30 \
    2>&1 | tee "$LOG_FILE"

echo ""
echo "[maintain] Complete. Log saved to: $LOG_FILE"
