#!/bin/bash
# E89/E90 — Autonomous overnight autoresearch loop.
#
# Runs four tasks at staggered intervals, in a single bash process, under nohup
# so it survives Claude session shutdown:
#
#   every 2h:  autoliterature_scanner.py    (papers + silicon council + model scout)
#   every 6h:  agent_council_registry.py    (dispatcher health smoke test)
#   every 8h:  e80_reflective_autoresearch  (silicon council reflects on trace)
#   every 4h:  vault dogfood audit          (12-agent self-critique)
#
# Each task is wrapped in `timeout` so it cannot hang the loop. Output goes to
# /tmp/autoresearch_overnight.log. Errors don't kill the loop.
#
# Launch:
#   nohup bash scripts/autoresearch_overnight.sh > /tmp/autoresearch_overnight.log 2>&1 &
#   echo $! > /tmp/autoresearch_overnight.pid
#
# Status:
#   tail -50 /tmp/autoresearch_overnight.log
#   ps -p $(cat /tmp/autoresearch_overnight.pid)
#
# Stop:
#   kill $(cat /tmp/autoresearch_overnight.pid)

set +e  # don't exit on any single failure
cd /home/mike-anderson/dev/cohezion

# SurrealDB v3 HTTP /sql protocol hangs on context-aware queries (confirmed May 2026).
# surreal_index.py detects this and falls back to JSONL — skip the 2s probe cost entirely.
export SURREAL_DISABLE=1

LOG=/tmp/autoresearch_overnight.log
echo "=== autoresearch_overnight start $(date -Iseconds) PID=$$ ===" | tee -a "$LOG"
echo "  schedule: lit-scan every 2h, dispatcher every 6h, reflect every 4h, dogfood every 8h" | tee -a "$LOG"

# Track last-run timestamps in seconds since epoch
LAST_LIT=0
LAST_DISPATCH=0
LAST_REFLECT=0
LAST_DOGFOOD=0

run_lit() {
  echo "--- [$(date -Iseconds)] autoliterature scanner ---" | tee -a "$LOG"
  timeout 240 uv run python scripts/autoliterature_scanner.py 2>&1 | tail -30 | tee -a "$LOG"
}

run_dispatch_check() {
  echo "--- [$(date -Iseconds)] dispatcher health smoke ---" | tee -a "$LOG"
  timeout 90 uv run python scripts/agent_council_registry.py 2>&1 | tail -10 | tee -a "$LOG"
}

run_reflect() {
  echo "--- [$(date -Iseconds)] reflective autoresearch ---" | tee -a "$LOG"
  timeout 90 uv run python scripts/e80_reflective_autoresearch.py 2>&1 | tail -20 | tee -a "$LOG"
}

run_dogfood() {
  echo "--- [$(date -Iseconds)] dogfood audit (vault state ping) ---" | tee -a "$LOG"
  # Lightweight: just touch the vault with a heartbeat observation
  timeout 60 uv run python -c "
import json, time
from datetime import datetime, timezone
obs_path = '/home/mike-anderson/vaults/cohezion-vault/memory/observations.jsonl'
with open(obs_path) as f:
    last_id = max((json.loads(line).get('id', 0) for line in f), default=0)
new_id = last_id + 1
ts = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
obs = {'id': new_id, 'timestamp': ts, 'type': 'change', 'project': 'cohezion',
       'title': f'autoresearch overnight heartbeat #{new_id}',
       'text': f'Overnight loop alive at {ts}. Last 4 vault titles: ' + ' | '.join(
            json.loads(l).get('title','')[:60]
            for l in open(obs_path).read().splitlines()[-4:])}
with open(obs_path, 'a') as f:
    f.write(json.dumps(obs) + chr(10))
print(f'heartbeat #{new_id} ok')
" 2>&1 | tail -3 | tee -a "$LOG"
}

# Fire each task once at start so the operator sees output immediately
NOW=$(date +%s)
echo "[startup] firing all 4 tasks once..." | tee -a "$LOG"
run_lit;       LAST_LIT=$(date +%s)
run_dispatch_check; LAST_DISPATCH=$(date +%s)
run_reflect;   LAST_REFLECT=$(date +%s)
run_dogfood;   LAST_DOGFOOD=$(date +%s)

# Steady-state loop
INTERVAL_LIT=$((2*3600))
INTERVAL_DISPATCH=$((6*3600))
INTERVAL_REFLECT=$((4*3600))
INTERVAL_DOGFOOD=$((8*3600))

while true; do
  sleep 300  # poll every 5 min
  NOW=$(date +%s)
  if (( NOW - LAST_LIT      >= INTERVAL_LIT      )); then run_lit;            LAST_LIT=$NOW;      fi
  if (( NOW - LAST_DISPATCH >= INTERVAL_DISPATCH )); then run_dispatch_check; LAST_DISPATCH=$NOW; fi
  if (( NOW - LAST_REFLECT  >= INTERVAL_REFLECT  )); then run_reflect;        LAST_REFLECT=$NOW;  fi
  if (( NOW - LAST_DOGFOOD  >= INTERVAL_DOGFOOD  )); then run_dogfood;        LAST_DOGFOOD=$NOW;  fi
done
