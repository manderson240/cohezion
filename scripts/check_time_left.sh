#!/bin/bash
# Script to check how much time is left in the Ollama maximization run

LOG_FILE="/home/mike-anderson/dev/cohezion/logs/ollama_maximizer.log"

if [ ! -f "$LOG_FILE" ]; then
    echo "Log file not found: $LOG_FILE"
    exit 1
fi

# Extract start time from log
START_TIME=$(grep "Starting Ollama usage maximization" "$LOG_FILE" | tail -1 | grep -o '[0-9]\{4\}-[0-9]\{2\}-[0-9]\{2\} [0-9]\{2\}:[0-9]\{2\}:[0-9]\{2\}')

if [ -z "$START_TIME" ]; then
    echo "Could not find start time in log"
    exit 1
fi

# Convert to epoch time
START_EPOCH=$(date -d "$START_TIME" +%s)
CURRENT_EPOCH=$(date +%s)

# Calculate elapsed time in hours
ELAPSED_HOURS=$(( (CURRENT_EPOCH - START_EPOCH) / 3600 ))
TOTAL_HOURS=10
REMAINING_HOURS=$(( TOTAL_HOURS - ELAPSED_HOURS ))

if [ $REMAINING_HOURS -lt 0 ]; then
    REMAINING_HOURS=0
fi

echo "Ollama Usage Maximization Time Check"
echo "===================================="
echo "Start Time: $START_TIME"
echo "Current Time: $(date)"
echo "Elapsed: ${ELAPSED_HOURS} hours"
echo "Total Runtime: ${TOTAL_HOURS} hours"
echo "Time Remaining: ${REMAINING_HOURS} hours"
echo ""
if [ $REMAINING_HOURS -eq 0 ]; then
    echo "✅ Maximization run has completed!"
else
    echo "⏳ Maximization run is still in progress..."
fi