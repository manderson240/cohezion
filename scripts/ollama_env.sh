#!/usr/bin/env bash
# Cohezion Ollama Environment Configuration
# Session 59: 3-Tier Hot/Warm/Cold Model Rotation
#
# Source this file before starting Ollama, or add to systemd override:
#   sudo systemctl edit ollama
#   [Service]
#   Environment="OLLAMA_MAX_LOADED_MODELS=4"
#   Environment="OLLAMA_NUM_PARALLEL=2"
#   ...

# Max concurrent models in memory (Tier 1 + Tier 2 = 4 slots)
export OLLAMA_MAX_LOADED_MODELS=4

# Parallel requests per model (2x KV cache per model, acceptable with Q8_0)
export OLLAMA_NUM_PARALLEL=2

# Keep models loaded 30 min after last use (warm tier default)
export OLLAMA_KEEP_ALIVE="30m"

# Enable flash attention (required for KV cache quantization)
export OLLAMA_FLASH_ATTENTION=1

# Quantize KV cache to Q8_0 (halves KV memory, negligible quality loss)
export OLLAMA_KV_CACHE_TYPE=q8_0

echo "Ollama environment configured:"
echo "  MAX_LOADED_MODELS=$OLLAMA_MAX_LOADED_MODELS"
echo "  NUM_PARALLEL=$OLLAMA_NUM_PARALLEL"
echo "  KEEP_ALIVE=$OLLAMA_KEEP_ALIVE"
echo "  FLASH_ATTENTION=$OLLAMA_FLASH_ATTENTION"
echo "  KV_CACHE_TYPE=$OLLAMA_KV_CACHE_TYPE"
