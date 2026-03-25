#!/usr/bin/env bash
# Headless plan execution for Cohezion.
# Runs /execute skill on a specified plan file with restricted tools and turn limits.
#
# Usage:
#   ./scripts/headless/execute-plan.sh <plan-path>
#
# Arguments:
#   plan-path  - Path to the plan file (e.g., docs/plans/2026-03-25-add-feature.md)
#
# Output is logged to ~/.cohezion-engine/logs/execute-<date>.log

set -euo pipefail

if [ "${1:-}" = "--help" ] || [ "${1:-}" = "-h" ] || [ -z "${1:-}" ]; then
    echo "Usage: $0 <plan-path>"
    echo ""
    echo "Execute an approved plan file autonomously using Claude Code."
    echo ""
    echo "Arguments:"
    echo "  plan-path   Path to the plan .md file"
    echo ""
    echo "Example:"
    echo "  $0 docs/plans/2026-03-25-add-auth.md"
    echo ""
    echo "Logs written to: ~/.cohezion-engine/logs/execute-<timestamp>.log"
    exit 0
fi

PLAN_PATH="$1"
LOG_DIR="${HOME}/.cohezion-engine/logs"
SLUG=$(basename "$PLAN_PATH" .md)
LOG_FILE="${LOG_DIR}/execute-${SLUG}-$(date +%Y%m%d-%H%M%S).log"

if [ ! -f "$PLAN_PATH" ]; then
    echo "Error: Plan file not found: $PLAN_PATH" >&2
    exit 1
fi

mkdir -p "$LOG_DIR"

echo "[execute-plan] Executing: $PLAN_PATH"
echo "[execute-plan] Log: $LOG_FILE"

claude -p "/execute $PLAN_PATH" \
    --allowedTools "Read,Edit,Write,Bash,Grep,Glob" \
    --max-turns 50 \
    2>&1 | tee "$LOG_FILE"

echo ""
echo "[execute-plan] Complete. Log saved to: $LOG_FILE"
