#!/bin/bash
# Check ROCm server startup manually

echo "=== ROCm Server Manual Test ==="
echo ""

# Set environment
export HSA_OVERRIDE_GFX_VERSION="11.0.0"
export HIP_VISIBLE_DEVICES="0"
export PATH="/opt/rocm/bin:$PATH"

# Check server binary
SERVER_BIN="/var/lib/lemonade/.cache/lemonade/bin/llamacpp/rocm/llama-server"
if [ ! -f "$SERVER_BIN" ]; then
    echo "❌ ROCm server binary not found: $SERVER_BIN"
    exit 1
fi

echo "✓ Server binary found: $SERVER_BIN"

# Check model exists
MODEL_PATH="/var/lib/lemonade/.cache/huggingface/hub/models--unsloth--DeepSeek-R1-0528-Qwen3-8B-GGUF/snapshots/*/DeepSeek-R1-0528-Qwen3-8B-Q4_1.gguf"
echo "✓ Model path: $MODEL_PATH"

# Test run with verbose output
echo ""
echo "=== Attempting startup (5 second test) ==="
timeout 5 "$SERVER_BIN" \
    -m "DeepSeek-R1-0528-Qwen3-8B-Q4_1.gguf" \
    --port 8003 \
    --ctx-size 1024 \
    --flash-attn \
    --verbose 2>&1 || echo ""

echo ""
echo "=== Exit code: $? ==="
