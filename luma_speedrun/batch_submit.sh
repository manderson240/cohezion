#!/bin/bash
# Submit batch of variants with rate limiting

set -e

echo "=== Batch Submission Script ==="
echo "Time: $(date '+%H:%M:%S')"
echo ""

# Submit MoE variants
for f in /home/mike-anderson/dev/cohezion/luma_speedrun/variants/moe/submission_*.py; do
    echo "Submitting MoE: $(basename $f)"
    timeout 120 popcorn-cli submit "$f" --mode test --gpu MI355X --leaderboard amd-moe-mxfp4 --no-tui 2>&1 | tail -3
    echo "Waiting for rate limit..."
    sleep 600
done

# Submit MLA variants
for f in /home/mike-anderson/dev/cohezion/luma_speedrun/variants/mla/submission_*.py; do
    echo "Submitting MLA: $(basename $f)"
    timeout 120 popcorn-cli submit "$f" --mode test --gpu MI355X --leaderboard amd-mixed-mla --no-tui 2>&1 | tail -3
    echo "Waiting for rate limit..."
    sleep 600
done

echo "Batch complete: $(date)"
