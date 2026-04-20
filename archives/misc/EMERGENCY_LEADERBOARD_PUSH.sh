#!/bin/bash
# EMERGENCY_LEADERBOARD_PUSH.sh - Submit to ACTUAL LEADERBOARD
# We've been submitting test/benchmark, NOT real leaderboard entries!

set -e

echo "🔴🔴🔴 EMERGENCY LEADERBOARD PUSH 🔴🔴🔴"
echo ""
echo "Current Status:"
echo "  ❌ All submissions: TEST or BENCHMARK mode"
echo "  ❌ NO ACTUAL LEADERBOARD ENTRIES"
echo "  ❌ NO OFFICIAL SCORES"
echo ""
echo "Action: Submitting to REAL LEADERBOARD NOW"
echo "Time: $(date)"
echo ""

WORKTREE="/home/mike-anderson/dev/cohezion/.worktrees/luma-breakthrough-sprint"
LOG="/tmp/leaderboard_push_$(date +%H%M).log"

# Function to submit to actual leaderboard
submit_leaderboard() {
    local kernel_dir=$1
    local submission_file=$2
    local leaderboard=$3
    local name=$4
    
    echo ""
    echo "🚀 [$name] LEGIT LEADERBOARD SUBMISSION"
    echo "    File: $submission_file"
    echo "    Leaderboard: $leaderboard"
    echo "    Mode: LEADERBOARD (official!)"
    echo ""
    
    cd "$kernel_dir"
    
    timeout 300 popcorn-cli submit "$submission_file" \
        --mode leaderboard \
        --gpu MI355X \
        --leaderboard "$leaderboard" \
        --no-tui 2>&1 | tee -a "$LOG" &
    
    echo "    PID: $!"
    echo ""
}

echo "================================================"
echo "LAUNCHING 3 REAL LEADERBOARD SUBMISSIONS"
echo "================================================"
echo ""

# Submit each kernel to ACTUAL leaderboard
submit_leaderboard \
    "$WORKTREE/luma_speedrun/amd-mixed-mla" \
    "submission_fixed.py" \
    "amd-mixed-mla" \
    "MLA"

submit_leaderboard \
    "$WORKTREE/luma_speedrun/amd-moe-mxfp4" \
    "submission.py" \
    "amd-moe-mxfp4" \
    "MoE"

submit_leaderboard \
    "$WORKTREE/luma_speedrun/amd-mxfp4-mm" \
    "submission.py" \
    "amd-mxfp4-mm" \
    "GEMM"

echo ""
echo "================================================"
echo "SUBMISSIONS IN FLIGHT"
echo "================================================"
echo ""
echo "Monitoring for 5 minutes..."
sleep 300

echo ""
echo "=== CHECKING LEADERBOARD STATUS ==="
echo ""

for lb in amd-mixed-mla amd-moe-mxfp4 amd-mxfp4-mm; do
    echo "--- $lb ---"
    timeout 10 popcorn-cli submissions list --leaderboard $lb 2>/dev/null | head -3 | tail -1
    echo ""
done

echo ""
echo "✅ EMERGENCY PUSH COMPLETE"
echo "Check: https://kernels.luma.io for actual scores"
echo ""
echo "Next: Monitor actual leaderboard standings"
