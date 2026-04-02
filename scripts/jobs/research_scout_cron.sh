#!/usr/bin/env bash
# Research Scout Cron — runs 1x daily (7am)
# Logs a research prompt for the next session to investigate
set -euo pipefail

COHEZION_DIR="/home/mike-anderson/dev/cohezion"
LOG_DIR="$COHEZION_DIR/logs/cron"
LOG="$LOG_DIR/research_scout_$(date +%Y%m%d_%H%M).log"
VAULT_DIR="$HOME/vaults/cohezion-vault/cerebellum"

cd "$COHEZION_DIR"
echo "=== Research Scout: $(date) ===" >> "$LOG"

DATE=$(date +%Y-%m-%d)

# Generate research topics note in vault
cat > "$VAULT_DIR/${DATE}-research-topics.md" << 'EOF'
---
title: "Daily Research Topics"
date: DATE_PLACEHOLDER
type: research-scout
---

# Research Topics for Today

## Priority Keywords
- "physics-grounded reinforcement learning"
- "training environments agents universes"
- "multi-agent safety CMDP Lagrangian"
- "JEPA world model latent planning"
- "compound AI orchestration skill refinement"
- "MCP agent-to-agent coordination"
- "reward hacking resistance structural"

## Tracked Papers
- V-JEPA 2.1 (arXiv:2603.14482) — dense loss upgrade path
- Causal-JEPA (arXiv:2602.11389) — object-level masking
- PI-RIG (arXiv:2511.06745) — physics-informed VAE
- ADRC-Lagrangian (arXiv:2601.18142) — 74% fewer violations
- HC-MAPPO-L (arXiv:2603.00129) — hierarchical constrained MAPPO
- Safe MARL Survey (arXiv:2505.17342) — CMDP framework

## Check
- Anthropic blog for new Universes/safety publications
- HuggingFace for new Gymnasium environments
- Safety-Gymnasium for updates
- MCP spec for Q3 agent-to-agent coordination
EOF

# Fix date placeholder
sed -i "s/DATE_PLACEHOLDER/$DATE/" "$VAULT_DIR/${DATE}-research-topics.md"

echo "Research topics note created: $VAULT_DIR/${DATE}-research-topics.md" >> "$LOG"

# Persist to SurrealDB
curl -s -X POST http://localhost:8001/sql \
  -H "Accept: application/json" \
  -H "surreal-ns: cohezion" \
  -H "surreal-db: cohezion" \
  -u "root:root" \
  -d "CREATE research_scout SET date = '$DATE', status = 'generated', created = time::now();" \
  >> "$LOG" 2>&1 || true

echo "=== Complete: $(date) ===" >> "$LOG"

find "$LOG_DIR" -name "research_scout_*.log" -mtime +30 -delete 2>/dev/null || true
