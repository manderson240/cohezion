#!/bin/bash
# PRODUCTION_NIGHTLY.sh - Robust overnight submission system

WORKTREE="/home/mike-anderson/dev/cohezion/.worktrees/luma-breakthrough-sprint"
LOG="/tmp/nightly_$(date +%Y%m%d).log"

echo "[$(date)] NIGHTLY SYSTEM STARTING - PID: $$" >> "$LOG"

cd "$WORKTREE"

round=0
while true; do
    round=$((round + 1))
    echo "[$(date)] === ROUND $round ===" >> "$LOG"
    
    # MLA
    echo "[$(date)] MLA submission..." >> "$LOG"
    cd "$WORKTREE/luma_speedrun/amd-mixed-mla"
    timeout 600 popcorn-cli submit submission.py --mode leaderboard --gpu MI355X --leaderboard amd-mixed-mla --no-tui >> "$LOG" 2>&1 &
    sleep 120
    
    # MoE
    echo "[$(date)] MoE submission..." >> "$LOG"
    cd "$WORKTREE/luma_speedrun/amd-moe-mxfp4"
    timeout 600 popcorn-cli submit submission.py --mode leaderboard --gpu MI355X --leaderboard amd-moe-mxfp4 --no-tui >> "$LOG" 2>&1 &
    sleep 120
    
    # GEMM
    echo "[$(date)] GEMM submission..." >> "$LOG"
    cd "$WORKTREE/luma_speedrun/amd-mxfp4-mm"
    timeout 600 popcorn-cli submit submission.py --mode leaderboard --gpu MI355X --leaderboard amd-mxfp4-mm --no-tui >> "$LOG" 2>&1 &
    
    echo "[$(date)] Sleeping 50 minutes..." >> "$LOG"
    sleep 3000
done
