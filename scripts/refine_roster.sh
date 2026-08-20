#!/bin/bash

# ==============================================================================
# Lemonade Server Model Roster Refinement Script (v2.0)
# Optimized for: 128GB Unified Memory Framework Desktop
# Purpose: Deeper purge of intermediate bloat, older architectures, and tiny assets.
# ==============================================================================

set -e

echo "======================================================================"
echo "🧹 Starting Lemonade Deep Model Registry Refinement..."
echo "======================================================================"

echo "--> Purging remaining intermediate and low-fidelity models..."

lemonade delete Granite-4.1-8B-GGUF || true
lemonade delete Qwen3-14B-GGUF || true
lemonade delete Qwen3.5-4B-MTP-GGUF || true
lemonade delete LMX-Omni-5.5B-Lite || true
lemonade delete gemma4-it-e2b-FLM || true
lemonade delete Mellum-4b-base-gguf-mellum-4b-base.Q8_0.gguf || true
lemonade delete Mellum-4b-base-gguf || true

echo "Removing low-fidelity utility engines..."
lemonade delete Whisper-Tiny || true

echo "✅ Phase 1 Deep Purge Completed."
echo "======================================================================"

echo "--> Priming elite utility assets..."

echo "Pulling Whisper-Large-v3-Turbo (elite fast speech-to-text)..."
lemonade pull Whisper-Large-v3-Turbo || true

echo "Ensuring embedding engine is ready..."
lemonade pull nomic-embed-text-v2-moe-GGUF || true

echo "======================================================================"
echo "🚀 Roster refined successfully! Here is your updated list:"
echo "======================================================================"
lemonade list
