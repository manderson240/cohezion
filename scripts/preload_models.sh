#!/usr/bin/env bash
# Cohezion Model Preloader — 3-Tier Hot/Warm/Cold Rotation
# Session 59: Preload Tier 1 (always hot) and Tier 2 (warm) models
#
# Usage: ./scripts/preload_models.sh [--tier1-only]
#
# Tier 1 (~5 GB): phi4-mini-reasoning + nomic-embed-text (always hot)
# Tier 2 (~43 GB): glm-4.7-flash + qwen3-coder:30b (warm, 30min keepalive)
# Tier 3 (on-demand): gpt-oss:20b, deepcoder:14b, nemotron-3-nano

set -euo pipefail

OLLAMA_URL="${OLLAMA_BASE_URL:-http://localhost:11434}"

preload() {
    local model="$1"
    local keep_alive="$2"
    echo "  Loading $model (keep_alive=$keep_alive)..."
    curl -sf "$OLLAMA_URL/api/generate" \
        -d "{\"model\": \"$model\", \"keep_alive\": $keep_alive}" \
        > /dev/null 2>&1 &
}

echo "=== Cohezion Model Preloader ==="
echo "Ollama: $OLLAMA_URL"
echo ""

# Tier 1: Always hot (keep_alive=-1 = indefinite)
echo "Tier 1 — Always Hot (~5 GB):"
preload "phi4-mini-reasoning" -1
preload "nomic-embed-text" -1

if [[ "${1:-}" == "--tier1-only" ]]; then
    wait
    echo ""
    echo "Tier 1 loaded. Skipping Tier 2."
    exit 0
fi

# Tier 2: Warm (keep_alive=-1 on preload, Ollama KEEP_ALIVE governs after use)
echo "Tier 2 — Warm (~43 GB):"
preload "glm-4.7-flash" -1
preload "qwen3-coder:30b" -1

wait
echo ""
echo "All Tier 1+2 models loaded."
echo "Memory usage: $(free -h 2>/dev/null | grep Mem | awk '{print $3 "/" $2}' || echo 'N/A')"
echo ""
echo "Tier 3 models (loaded on-demand):"
echo "  - gpt-oss:20b (~16 GB)"
echo "  - deepcoder:14b (~12 GB)"
echo "  - nemotron-3-nano (~27 GB, 1M context)"
