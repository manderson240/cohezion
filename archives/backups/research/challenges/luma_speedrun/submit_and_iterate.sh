#!/bin/bash
# Autonomous submission script for overnight operation.
# Usage: ./submit_and_iterate.sh [kernel] [mode]
# Example: ./submit_and_iterate.sh gemm benchmark

KERNEL="${1:-gemm}"
MODE="${2:-test}"

case "$KERNEL" in
    gemm) DIR="amd-mxfp4-mm"; LB="amd-mxfp4-mm" ;;
    moe) DIR="amd-moe-mxfp4"; LB="amd-moe-mxfp4" ;;
    mla) DIR="amd-mixed-mla"; LB="amd-mixed-mla" ;;
    *) echo "Unknown kernel: $KERNEL"; exit 1 ;;
esac

echo "$(date): Submitting $KERNEL ($MODE) from $DIR/submission.py"
RESULT=$(popcorn-cli submit --no-tui --mode "$MODE" --gpu MI355X --leaderboard "$LB" "$DIR/submission.py" 2>&1)

# Check for rate limit
if echo "$RESULT" | grep -q "Rate limit"; then
    WAIT=$(echo "$RESULT" | grep -oP 'Try again in \K[0-9]+')
    echo "$(date): Rate limited, wait ${WAIT}s"
    exit 2
fi

# Check for success
if echo "$RESULT" | grep -q "Testing successful\|Benchmarking successful"; then
    echo "$(date): SUCCESS"
    # Extract timing if benchmark
    echo "$RESULT" | grep -E "⏱|µs" | head -10
else
    echo "$(date): FAILED"
    echo "$RESULT" | grep -E "error|Error|failed|❌" | head -5
fi
