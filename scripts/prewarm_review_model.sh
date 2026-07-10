#!/usr/bin/env bash
# scripts/prewarm_review_model.sh — pre-warm a local inference model for code review.
#
# Acquires the fleet_lock:modelload, loads the model via Lemonade OmniRouter,
# waits for it to become available, then releases the lock.
#
# This prevents the LRU eviction / HTTP 500 issue that occurred during the
# consolidation campaign code review (Qwen3-Coder-30B was evicted before the
# review agent could use it).
#
# Usage:
#   bash scripts/prewarm_review_model.sh                           # default: Qwen3-Coder-30B
#   bash scripts/prewarm_review_model.sh Gemma-4-31B-it-GGUF       # custom model
#   bash scripts/prewarm_review_model.sh Qwen3-Coder-30B-A3B-Instruct-GGUF 16384  # custom ctx_size
#
# Exit codes:
#   0 = model loaded and ready
#   1 = preflight failed (do not proceed)
#   2 = load failed
#   3 = model not available after timeout

set -euo pipefail

MODEL="${1:-Qwen3-Coder-30B-A3B-Instruct-GGUF}"
CTX_SIZE="${2:-16384}"
ROUTER="http://localhost:13305"
TIMEOUT=120  # seconds to wait for model to appear in /v1/models

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=== Pre-warm: $MODEL (ctx_size=$CTX_SIZE) ==="

# Step 1: Preflight check
echo "[1/4] Running preflight_fleet.sh..."
if ! bash "$SCRIPT_DIR/preflight_fleet.sh"; then
  echo "❌ Preflight failed — do not start model load."
  exit 1
fi
echo "✅ Preflight passed."

# Step 2: Check if model is already loaded
echo "[2/4] Checking if model is already loaded..."
if curl -s "$ROUTER/v1/models" | python3 -c "
import sys, json
data = json.load(sys.stdin)
models = [m['id'] for m in data.get('data', [])]
sys.exit(0 if '$MODEL' in models else 1)
" 2>/dev/null; then
  echo "✅ Model already loaded — no pre-warm needed."
  exit 0
fi
echo "Model not loaded. Proceeding with load."

# Step 3: Acquire fleet lock and load model
echo "[3/4] Acquiring fleet_lock:modelload and loading model..."
python3 -c "
import asyncio, json, subprocess, time
import urllib.request

async def main():
    # Acquire fleet lock
    try:
        from cohezion.researcher.daily_researcher import FleetLock
        lock = FleetLock()
        async with lock.acquire('modelload', timeout=30.0):
            print('  Fleet lock acquired.')
            # Load model
            body = json.dumps({
                'model_name': '$MODEL',
                'ctx_size': $CTX_SIZE,
                'save_options': True
            }).encode()
            req = urllib.request.Request(
                '$ROUTER/api/v1/load',
                data=body,
                headers={'Content-Type': 'application/json'},
                method='POST'
            )
            resp = urllib.request.urlopen(req, timeout=60)
            result = json.loads(resp.read())
            status = result.get('status', 'unknown')
            print(f'  Load response: status={status}')
            if status != 'success':
                print(f'  ❌ Load failed: {result}')
                return False
        print('  Fleet lock released.')
        return True
    except ImportError:
        print('  FleetLock not available — loading without lock (single-user mode).')
        body = json.dumps({
            'model_name': '$MODEL',
            'ctx_size': $CTX_SIZE,
            'save_options': True
        }).encode()
        req = urllib.request.Request(
            '$ROUTER/api/v1/load',
            data=body,
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        resp = urllib.request.urlopen(req, timeout=60)
        result = json.loads(resp.read())
        status = result.get('status', 'unknown')
        print(f'  Load response: status={status}')
        return status == 'success'

result = asyncio.run(main())
import sys
sys.exit(0 if result else 2)
"

LOAD_EXIT=$?
if [ $LOAD_EXIT -ne 0 ]; then
  echo "❌ Model load failed."
  exit 2
fi

# Step 4: Wait for model to appear in /v1/models
echo "[4/4] Waiting for model to appear in /v1/models..."
START=$SECONDS
while true; do
  if curl -s "$ROUTER/v1/models" | python3 -c "
import sys, json
data = json.load(sys.stdin)
models = [m['id'] for m in data.get('data', [])]
sys.exit(0 if '$MODEL' in models else 1)
" 2>/dev/null; then
    echo "✅ Model '$MODEL' is now available."
    exit 0
  fi
  if [ $((SECONDS - START)) -gt $TIMEOUT ]; then
    echo "❌ Timeout waiting for model to appear ($TIMEOUT s)."
    exit 3
  fi
  sleep 2
done