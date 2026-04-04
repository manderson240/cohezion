#!/bin/bash
# OVERNIGHT_LEADERBOARD_CRON.sh - Makes ACTUAL leaderboard submissions

WORKTREE="/home/mike-anderson/dev/cohezion/.worktrees/luma-breakthrough-sprint"
LOGFILE="/tmp/overnight_$(date +%Y%m%d_%H%M).log"

echo "[$(date)] Starting overnight leaderboard automation" >> "$LOGFILE"

# Submit MLA
echo "[$(date)] Submitting MLA..." >> "$LOGFILE"
cd "$WORKTREE/luma_speedrun/amd-mixed-mla"
timeout 300 popcorn-cli submit submission.py --mode leaderboard --gpu MI355X --leaderboard amd-mixed-mla --no-tui >> "$LOGFILE" 2>&1 &
sleep 60

# Submit MoE
echo "[$(date)] Submitting MoE..." >> "$LOGFILE"
cd "$WORKTREE/luma_speedrun/amd-moe-mxfp4"
timeout 300 popcorn-cli submit submission.py --mode leaderboard --gpu MI355X --leaderboard amd-moe-mxfp4 --no-tui >> "$LOGFILE" 2>&1 &
sleep 60

# Submit GEMM
echo "[$(date)] Submitting GEMM..." >> "$LOGFILE"
cd "$WORKTREE/luma_speedrun/amd-mxfp4-mm"
timeout 300 popcorn-cli submit submission.py --mode leaderboard --gpu MI355X --leaderboard amd-mxfp4-mm --no-tui >> "$LOGFILE" 2>&1 &

echo "[$(date)] All submissions launched" >> "$LOGFILE"
