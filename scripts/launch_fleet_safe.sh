#!/bin/bash
# Strix Halo — verify unified Lemonade router on :13305.
# Previously launched 4 per-lane lemond daemons (13306-13309); those are
# now handled by the system lemond.service (the unified router on :13305).
#
# Usage:
#   bash scripts/launch_fleet_safe.sh

set -u

echo "======================================================================"
echo "🏛️  STRIX HALO — UNIFIED ROUTER CHECK (:13305)"
echo "======================================================================"

ROUTER="http://localhost:13305"

if curl -sf --max-time 3 "$ROUTER/v1/models" > /dev/null 2>&1; then
  MODELS=$(curl -sf --max-time 3 "$ROUTER/v1/models" | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d.get('data',[])), 'models')" 2>/dev/null || echo "?")
  echo "✅ Unified router :13305 UP — $MODELS available"
else
  echo "❌ Unified router :13305 DOWN"
  echo "   Restart: sudo systemctl start lemond"
  exit 1
fi

echo "======================================================================"
echo "✅ ROUTER CHECK COMPLETE"
echo "Probe: curl -s http://localhost:13305/v1/models | python3 -c \"import sys,json; d=json.load(sys.stdin); print([m['id'] for m in d['data']])\""
echo "======================================================================"
