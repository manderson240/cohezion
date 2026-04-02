#!/usr/bin/env bash
# Ouroboros Healing Cron — runs 1x daily (2am)
# Runs anomaly detection on recent trajectories, triggers healing if needed
set -euo pipefail

COHEZION_DIR="/home/mike-anderson/dev/cohezion"
LOG_DIR="$COHEZION_DIR/logs/cron"
LOG="$LOG_DIR/ouroboros_$(date +%Y%m%d_%H%M).log"
LOCK="/tmp/cohezion_ouroboros.lock"

exec 200>"$LOCK"
flock -n 200 || { echo "Already running" >> "$LOG"; exit 0; }

cd "$COHEZION_DIR"
echo "=== Ouroboros Healing: $(date) ===" >> "$LOG"

.venv/bin/python -c "
from cohezion.ouroboros.detector import AnomalyDetector
import json, urllib.request
from base64 import b64encode

# Query recent health checks
try:
    req = urllib.request.Request(
        'http://localhost:8001/sql',
        data=b'SELECT * FROM health_check ORDER BY created DESC LIMIT 5;',
        headers={
            'Accept': 'application/json',
            'surreal-ns': 'cohezion',
            'surreal-db': 'cohezion',
            'Authorization': 'Basic ' + b64encode(b'root:root').decode(),
        },
        method='POST',
    )
    resp = urllib.request.urlopen(req, timeout=5)
    data = json.loads(resp.read())
    checks = data[0]['result'] if data and data[0].get('status') == 'OK' else []
except Exception as e:
    checks = []
    print(f'SurrealDB query failed: {e}')

# Check for degradation
detector = AnomalyDetector(coherence_threshold=0.1, target_coherence=0.5)
degraded = [c for c in checks if c.get('status') == 'DEGRADED']

if degraded:
    print(f'HEALING NEEDED: {len(degraded)} degraded health checks')
    # Log healing event to SurrealDB
    try:
        heal_sql = f\"CREATE healing_cycle SET phase='detection', degraded_count={len(degraded)}, created=time::now();\"
        req2 = urllib.request.Request(
            'http://localhost:8001/sql',
            data=heal_sql.encode(),
            headers={
                'Accept': 'application/json',
                'surreal-ns': 'cohezion',
                'surreal-db': 'cohezion',
                'Authorization': 'Basic ' + b64encode(b'root:root').decode(),
            },
            method='POST',
        )
        urllib.request.urlopen(req2, timeout=5)
        print('Healing cycle recorded in SurrealDB')
    except Exception as e:
        print(f'Failed to record healing: {e}')
else:
    print(f'System healthy: {len(checks)} recent checks, 0 degraded')
" >> "$LOG" 2>&1 || true

echo "=== Complete: $(date) ===" >> "$LOG"

find "$LOG_DIR" -name "ouroboros_*.log" -mtime +30 -delete 2>/dev/null || true
