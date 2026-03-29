#!/bin/bash
# AIMO Compound Research Session Runner
# Usage: ./run_compound_session.sh [duration_hours] [problem_count]

DURATION=${1:-8}
PROBLEMS=${2:-10}

echo "========================================"
echo "AIMO Compound Research Session"
echo "========================================"
echo "Duration: ${DURATION}h"
echo "Problems: ${PROBLEMS}"
echo "Start: $(date)"
echo "========================================"

# Create session directory
SESSION_ID="aimo_$(date +%Y%m%d_%H%M%S)"
mkdir -p "sessions/${SESSION_ID}"

# Run compound driver
python aimo_compound_driver.py \
    --duration ${DURATION} \
    --problems ${PROBLEMS} \
    --threshold 0.5 \
    --max-cycles 20 \
    2>&1 | tee "sessions/${SESSION_ID}/session.log"

echo ""
echo "========================================"
echo "Session Complete"
echo "End: $(date)"
echo "Logs: sessions/${SESSION_ID}/"
echo "========================================"
