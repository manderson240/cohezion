#!/usr/bin/env bash
# Compound Training Cron — runs 3x daily (6am, 12pm, 6pm)
# Trains SAC dense 100K, persists to SurrealDB, triggers SkillRefiner on new best
set -euo pipefail

COHEZION_DIR="/home/mike-anderson/dev/cohezion"
LOG_DIR="$COHEZION_DIR/logs/cron"
LOG="$LOG_DIR/compound_train_$(date +%Y%m%d_%H%M).log"
LOCK="/tmp/cohezion_compound_train.lock"

# Prevent concurrent runs
exec 200>"$LOCK"
flock -n 200 || { echo "Already running" >> "$LOG"; exit 0; }

cd "$COHEZION_DIR"
echo "=== Compound Training Cron: $(date) ===" >> "$LOG"

# Run compound training cycle (SAC dense, auto-persist)
CUDA_VISIBLE_DEVICES="" HIP_VISIBLE_DEVICES="" \
  .venv/bin/python scripts/compound_training_cycle.py \
    --algo SAC --steps 100000 >> "$LOG" 2>&1 || true

echo "=== Complete: $(date) ===" >> "$LOG"

# Cleanup old logs (keep 30 days)
find "$LOG_DIR" -name "compound_train_*.log" -mtime +30 -delete 2>/dev/null || true
