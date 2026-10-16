#!/usr/bin/env bash
# Autonomous 24/7 Continuous Daily Allotment Engine Supervisor Daemon
set -e
WORKSPACE="/home/mike-anderson/.gemini/antigravity-cli/worktrees/cohezion/ollama_lemonade_kaggle_push"
cd "$WORKSPACE"
export PYTHONPATH="$WORKSPACE/src:$WORKSPACE:$PYTHONPATH"

while true; do
    echo "[$(date -u)] Starting continuous_daily_allotment_engine..."
    python3 scripts/kaggle/continuous_daily_allotment_engine.py || true
    echo "[$(date -u)] Allotment engine exited with code $?. Restarting in 15 seconds..."
    sleep 15
done
