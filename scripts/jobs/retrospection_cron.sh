#!/usr/bin/env bash
# Retrospection Cron — runs 2x daily (8am, 8pm)
# Queries SurrealDB for recent executions, generates daily summary
set -euo pipefail

COHEZION_DIR="/home/mike-anderson/dev/cohezion"
LOG_DIR="$COHEZION_DIR/logs/cron"
LOG="$LOG_DIR/retrospection_$(date +%Y%m%d_%H%M).log"
VAULT_DIR="$HOME/vaults/cohezion-vault/cerebellum"

cd "$COHEZION_DIR"
echo "=== Retrospection: $(date) ===" >> "$LOG"

# Query recent training runs from SurrealDB
RUNS=$(curl -s -X POST http://localhost:8001/sql \
  -H "Accept: application/json" \
  -H "surreal-ns: cohezion" \
  -H "surreal-db: cohezion" \
  -u "root:root" \
  -d "SELECT count() FROM training_run GROUP ALL;" 2>/dev/null || echo "[]")

LEARNINGS=$(curl -s -X POST http://localhost:8001/sql \
  -H "Accept: application/json" \
  -H "surreal-ns: cohezion" \
  -H "surreal-db: cohezion" \
  -u "root:root" \
  -d "SELECT count() FROM learning GROUP ALL;" 2>/dev/null || echo "[]")

echo "Training runs: $RUNS" >> "$LOG"
echo "Learnings: $LEARNINGS" >> "$LOG"

# Check KEY_LEARNINGS line count
KL_LINES=$(wc -l < "$COHEZION_DIR/src/cohezion/knowledge_graph/KEY_LEARNINGS.md" 2>/dev/null || echo "0")
echo "KEY_LEARNINGS.md: $KL_LINES lines" >> "$LOG"
if [ "$KL_LINES" -gt 280 ]; then
  echo "WARNING: KEY_LEARNINGS.md approaching 300-line limit ($KL_LINES/300)" >> "$LOG"
fi

# Trigger SkillRefiner training consumption
.venv/bin/python -c "
from cohezion.compound.skill_refiner import SkillRefiner
sr = SkillRefiner()
result = sr.refine_from_training_runs()
print(f'SkillRefiner: {result or \"no updates\"}')
" >> "$LOG" 2>&1 || true

# Generate vault daily note
DATE=$(date +%Y-%m-%d)
TIME=$(date +%H:%M)
VAULT_NOTE="$VAULT_DIR/${DATE}-auto-retrospection-${TIME}.md"
cat > "$VAULT_NOTE" << EOF
---
title: "Auto-Retrospection: ${DATE} ${TIME}"
date: ${DATE}
type: auto-retrospection
---

# Auto-Retrospection ${DATE} ${TIME}

- KEY_LEARNINGS.md: ${KL_LINES}/300 lines
- SurrealDB training runs: $(echo "$RUNS" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d[0]['result'][0]['count'] if d and d[0].get('status')=='OK' else '?')" 2>/dev/null || echo "?")
- SurrealDB learnings: $(echo "$LEARNINGS" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d[0]['result'][0]['count'] if d and d[0].get('status')=='OK' else '?')" 2>/dev/null || echo "?")
EOF

echo "Vault note: $VAULT_NOTE" >> "$LOG"
echo "=== Complete: $(date) ===" >> "$LOG"

find "$LOG_DIR" -name "retrospection_*.log" -mtime +30 -delete 2>/dev/null || true
