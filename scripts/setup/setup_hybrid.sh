#!/bin/bash
# Setup Hybrid NPU/GPU/Cloud Inference Swarm

set -e

echo "=== Hybrid Inference Setup ==="
echo ""

# 1. Ensure Lemonade is running
echo "Step 1: Checking Lemonade NPU..."
if ! curl -s http://localhost:13305/v1/models > /dev/null 2>&1; then
    echo "  Starting Lemonade server..."
    nohup lemond --port 13305 --host 127.0.0.1 > /tmp/lemonade.log 2>&1 &
    sleep 5
fi
echo "  ✓ Lemonade ready"

# 2. Ensure Ollama is running
echo "Step 2: Checking Ollama Cloud..."
if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "  Starting Ollama..."
    nohup ollama serve > /tmp/ollama.log 2>&1 &
    sleep 3
fi
echo "  ✓ Ollama ready"

# 3. Pre-load NPU model
echo "Step 3: Loading NPU model (qwen3.5-4b-FLM)..."
if lemonade list | grep -q "qwen3.5-4b-FLM.*No"; then
    echo "  Downloading (this may take a while)..."
    lemonade pull qwen3.5-4b-FLM &
    echo "  Download initiated in background"
else
    echo "  Model available"
fi

# 4. Pre-load Cloud fallback
echo "Step 4: Loading Cloud fallback (gemma4:e4b)..."
ollama pull gemma4:e4b 2>/dev/null || echo "  Cloud model ready"

# 5. Create systemd service for hybrid router (optional)
echo "Step 5: Creating hybrid router service..."
cat > /tmp/hybrid-router.service << 'EOF'
[Unit]
Description=Hybrid NPU/GPU/Cloud Swarm Router
After=network.target

[Service]
Type=simple
User=%I
WorkingDirectory=/home/%I/dev/cohezion
ExecStart=/usr/bin/python3 hybrid_swarm_router.py --daemon
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

echo ""
echo "=== Hybrid Setup Complete ==="
echo ""
echo "Backends:"
echo "  NPU (XDNA2): http://localhost:13305 - qwen3.5-4b-FLM"
echo "  GPU (ROCm):  http://localhost:13305 - Currently fixed (see fix_rocm_gfx1151.sh)"
echo "  Cloud:       http://localhost:11434 - gemma4:e4b, gemma4:e2b"
echo ""
echo "To use hybrid routing:"
echo "  python3 hybrid_swarm_router.py"
echo ""
echo "To fix ROCm for full Gemma 4 GPU support:"
echo "  sudo ./fix_rocm_gfx1151.sh && sudo reboot"
echo ""
