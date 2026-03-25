#!/bin/bash
# 4-hour K-Search evolution session with auto-restart on convergence
# Usage: bash run_4hr.sh

set -euo pipefail
cd "$(dirname "$0")"

LOG_DIR="/tmp/ksearch-4hr"
mkdir -p "$LOG_DIR"
START_TIME=$(date +%s)
END_TIME=$((START_TIME + 4 * 3600))  # 4 hours from now
BATCH=1
CYCLES_PER_BATCH=100  # Run 100 cycles per batch (~15 min)
MODEL="qwen3-coder-next:cloud"
TOTAL_CYCLES=0
TOTAL_INSERTS=0
TOTAL_PRUNES=0

echo "=== K-Search 4-Hour Session ==="
echo "Start: $(date)"
echo "End:   $(date -d @$END_TIME)"
echo "Model: $MODEL"
echo "Log dir: $LOG_DIR"
echo ""

while [ "$(date +%s)" -lt "$END_TIME" ]; do
    LOG="$LOG_DIR/batch_${BATCH}.log"
    echo "--- Batch $BATCH ($(date +%H:%M:%S)) ---"

    # Run a batch of cycles
    python3 -u driver.py \
        --dry-run-llm \
        --max-cycles "$CYCLES_PER_BATCH" \
        --model "$MODEL" \
        > "$LOG" 2>&1 || true

    # Count stats from this batch
    BATCH_CYCLES=$(grep -c "^.*Cycle" "$LOG" 2>/dev/null || echo 0)
    BATCH_INSERTS=$(grep -c "LLM INSERT" "$LOG" 2>/dev/null || echo 0)
    BATCH_PRUNES=$(grep -c "PRUNE" "$LOG" 2>/dev/null || echo 0)
    BATCH_UPDATES=$(grep -c "LLM UPDATE" "$LOG" 2>/dev/null || echo 0)
    CONVERGED=$(grep -c "CONVERGED" "$LOG" 2>/dev/null || echo 0)

    TOTAL_CYCLES=$((TOTAL_CYCLES + BATCH_CYCLES))
    TOTAL_INSERTS=$((TOTAL_INSERTS + BATCH_INSERTS))
    TOTAL_PRUNES=$((TOTAL_PRUNES + BATCH_PRUNES))

    echo "  Cycles: $BATCH_CYCLES | Inserts: $BATCH_INSERTS | Updates: $BATCH_UPDATES | Prunes: $BATCH_PRUNES"
    echo "  Total: $TOTAL_CYCLES cycles, $TOTAL_INSERTS inserts, $TOTAL_PRUNES prunes"

    # If converged, reset convergence state by touching trees (add synthetic attempt)
    if [ "$CONVERGED" -gt 0 ]; then
        echo "  Converged — resetting for next batch (new R-Zero challengers will be injected)"
    fi

    # Save trees to git every 5 batches
    if [ $((BATCH % 5)) -eq 0 ]; then
        cd /home/mike-anderson/dev/cohezion
        git add research/challenges/luma_amd_speedrun/autoresearch/tree/ 2>/dev/null
        git commit -m "chore: K-Search batch $BATCH ($TOTAL_CYCLES cycles, $TOTAL_INSERTS inserts, $TOTAL_PRUNES prunes)" \
            --allow-empty 2>/dev/null || true
        cd research/challenges/luma_amd_speedrun/autoresearch
        echo "  [git commit at batch $BATCH]"
    fi

    BATCH=$((BATCH + 1))

    # Brief pause between batches
    sleep 2
done

# Final commit
cd /home/mike-anderson/dev/cohezion
git add research/challenges/luma_amd_speedrun/autoresearch/tree/ 2>/dev/null
git commit -m "feat: K-Search 4hr session complete ($TOTAL_CYCLES cycles, $TOTAL_INSERTS inserts, $TOTAL_PRUNES prunes)

Co-Authored-By: Claude <noreply@anthropic.com>" --allow-empty 2>/dev/null || true

echo ""
echo "=== Session Complete ==="
echo "Duration: $(( ($(date +%s) - START_TIME) / 60 )) minutes"
echo "Total cycles: $TOTAL_CYCLES"
echo "Total inserts: $TOTAL_INSERTS"
echo "Total prunes: $TOTAL_PRUNES"
echo "Batches: $((BATCH - 1))"

# Final tree stats
cd research/challenges/luma_amd_speedrun/autoresearch
python3 -c "
import json
for k in ['moe', 'gemm', 'mla']:
    d = json.load(open(f'tree/{k}_tree.json'))
    active = [n for n in d['nodes'].values() if n['status'] == 'active']
    llm = [n for n in d['nodes'].values() if 'LLM-proposed' in n.get('notes','')]
    print(f'{k.upper()}: {len(d[\"nodes\"])} nodes, {len(active)} active, {len(llm)} LLM-proposed')
"
