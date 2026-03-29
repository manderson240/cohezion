#!/bin/bash
# Monitor submission progress until 7 AM EST

TARGET_HOUR=7
LOG_FILE="/home/mike-anderson/dev/cohezion/luma_speedrun/submission_monitor.log"

echo "Monitoring submissions until ${TARGET_HOUR}:00 EST..." > "$LOG_FILE"
echo "Started at: $(date)" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

while [ $(date +%H) -lt $TARGET_HOUR ]; do
    clear
    echo "=== Submission Monitor ==="
    echo "Time: $(date '+%H:%M:%S') | Target: ${TARGET_HOUR}:00:00"
    echo ""
    
    for lb in amd-mixed-mla amd-moe-mxfp4 amd-mxfp4-mm; do
        echo "--- $lb ---"
        popcorn-cli submissions list --leaderboard $lb 2>&1 | head -5
        echo ""
    done
    
    echo "Recent activity (last 5 submissions):"
    for lb in amd-mixed-mla amd-moe-mxfp4 amd-mxfp4-mm; do
        popcorn-cli submissions list --leaderboard $lb 2>&1 | grep -E "^66[0-9]{4}" | head -5
    done
    
    sleep 120  # Update every 2 minutes
done

echo "Time limit reached: $(date)" >> "$LOG_FILE"
echo "Final status:" >> "$LOG_FILE"
for lb in amd-mixed-mla amd-moe-mxfp4 amd-mxfp4-mm; do
    echo "--- $lb ---" >> "$LOG_FILE"
    popcorn-cli submissions list --leaderboard $lb 2>&1 | head -10 >> "$LOG_FILE"
done
