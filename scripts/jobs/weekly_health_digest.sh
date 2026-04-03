#!/bin/bash
# Weekly Health Digest — Generate all health reports for vault cortex
# Runs Sundays at 1am via cron

set -euo pipefail

COHEZION_DIR="${HOME}/dev/cohezion"
VAULT_DIR="${HOME}/vaults/cohezion-vault"

echo "=== Weekly Health Digest: $(date -Iseconds) ==="

cd "$COHEZION_DIR"

# Generate unified health dashboard
echo "Generating unified health dashboard..."
uv run python3 tools/unified_health_dashboard.py --output vault

# Generate graph health dashboard
echo "Generating graph health dashboard..."
uv run python3 tools/graph_health_dashboard.py --output vault

# Generate data product health report
echo "Generating data product health report..."
uv run python3 tools/data_product_health.py --output vault

# Generate dream insights
echo "Generating dream insights..."
uv run python3 tools/dream_quality_report.py --output vault --days 7

# Generate TOE bridge
echo "Generating TOE bridge..."
uv run python3 tools/dream_toe_bridge.py --output vault --days 14

echo "=== Weekly digest complete ==="
echo "Reports saved to: ${VAULT_DIR}/cortex/"
