#!/bin/bash
# Continuous submission loop until 7 AM EST

while [ $(date +%H) -lt 7 ]; do
    clear
    echo "=== AMD Speedrun Submission Monitor ==="
    echo "Time: $(date '+%H:%M:%S')"
    echo "Target: 07:00:00"
    echo ""
    
    for lb in amd-mixed-mla amd-moe-mxfp4 amd-mxfp4-mm; do
        echo "--- $lb ---"
        popcorn-cli submissions list --leaderboard $lb 2>/dev/null | grep "^67" | head -3
        echo ""
    done
    
    sleep 60
done

echo "Time limit reached!"
