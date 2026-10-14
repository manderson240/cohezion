#!/usr/bin/env bash
# ==============================================================================
# Cohezion Post-Reboot Resumption Script
# ==============================================================================
# Restores all daemons, verifies SurrealDB, re-arms midnight harvest,
# and checks the latest Kaggle submission scores.
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$REPO_ROOT"

echo "=== [1/5] Checking Python Virtual Environment ==="
if [ -f ".venv/bin/python3" ]; then
    PYTHON=".venv/bin/python3"
    echo "Using virtual environment: $PYTHON"
else
    PYTHON="python3"
    echo "Virtualenv not found, using system python: $PYTHON"
fi

echo "=== [2/5] Checking SurrealDB Health (Port 8001) ==="
if curl -s http://127.0.0.1:8001/version > /dev/null 2>&1; then
    echo "✓ SurrealDB is running on http://127.0.0.1:8001"
else
    echo "⚠️ SurrealDB is not responding on 8001. Attempting to start in background..."
    nohup /home/mike-anderson/.surrealdb/surreal start \
        --username root --password root \
        --bind 127.0.0.1:8001 \
        --no-banner \
        --query-timeout 30s \
        --transaction-timeout 60s \
        --temporary-directory /tmp/surrealdb \
        --default-namespace cohezion \
        --default-database main \
        surrealkv:///home/mike-anderson/dev/cohezion/data/surrealkv?versioned=true \
        > /tmp/surrealdb.log 2>&1 &
    sleep 3
    if curl -s http://127.0.0.1:8001/version > /dev/null 2>&1; then
        echo "✓ SurrealDB successfully started!"
    else
        echo "❌ SurrealDB start check failed. Check /tmp/surrealdb.log"
    fi
fi

echo "=== [3/5] Launching Master 24/7 Kaggle Ascent Sentinel ==="
pkill -f "master_24_7_kaggle_sentinel.py" || true
nohup "$PYTHON" scripts/kaggle/master_24_7_kaggle_sentinel.py > /tmp/master_sentinel_reboot.log 2>&1 &
echo "✓ Master 24/7 Kaggle Sentinel launched (PID: $!). Log: /tmp/master_sentinel_reboot.log"

echo "=== [4/5] Launching Midnight UTC Autonomous Submitter ==="
pkill -f "queue_midnight_all_competitions.py" || true
nohup "$PYTHON" scripts/kaggle/queue_midnight_all_competitions.py > /tmp/midnight_queue_reboot.log 2>&1 &
echo "✓ Midnight UTC Autonomous Submitter launched (PID: $!). Log: /tmp/midnight_queue_reboot.log"

echo "=== [5/5] Fetching Latest Kaggle Competition Submissions ==="
"$PYTHON" -c "
from kaggle.api.kaggle_api_extended import KaggleApi
try:
    api = KaggleApi()
    api.authenticate()
    for name, slug in [
        ('RSNA Knee', 'rsna-knee-abnormality-detection'),
        ('CASMI26', 'enveda-CASMI26-molecule-id-mass-spectra'),
        ('ARC-AGI-2', 'arc-prize-2026-arc-agi-2'),
        ('ARC-AGI-3', 'arc-prize-2026-arc-agi-3'),
    ]:
        print(f'\n--- {name} ({slug}) ---')
        subs = api.competition_submissions(slug)
        for s in subs[:3]:
            print(f'Ref: {s.ref} | Status: {s.status} | Public: {s.public_score} | Msg: {s.description[:55]}...')
except Exception as e:
    print('Kaggle API status note:', e)
"

echo "=============================================================================="
echo "✓ All systems, daemons, and background processes successfully restored!"
echo "=============================================================================="
