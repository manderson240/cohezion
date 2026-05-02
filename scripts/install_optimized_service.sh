#!/bin/bash
# Install Lemonade with AMD Optimizations
# Usage: sudo ./install_optimized_service.sh

set -e

echo "========================================"
echo "Installing Lemonade Optimized Service"
echo "========================================"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "❌ This script must be run with sudo"
    exit 1
fi

# Verify files exist
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_FILE="$SCRIPT_DIR/lemonade-optimized.service"
PROFILE_FILE="$SCRIPT_DIR/lemonade-gpu-profile.service"

if [ ! -f "$SERVICE_FILE" ]; then
    echo "❌ Service file not found: $SERVICE_FILE"
    exit 1
fi

if [ ! -f "$PROFILE_FILE" ]; then
    echo "❌ Profile service file not found: $PROFILE_FILE"
    exit 1
fi

echo "✓ Service files found"

# Check GPU device path
GPU_PATH="/sys/class/drm/card1/device/power_dpm_force_performance_level"
if [ -f "$GPU_PATH" ]; then
    echo "✓ GPU power profile path exists"
    CURRENT_PROFILE=$(cat "$GPU_PATH" 2>/dev/null || echo "unknown")
    echo "  Current profile: $CURRENT_PROFILE"
else
    echo "⚠ GPU power profile path not found: $GPU_PATH"
    echo "  Power profile service may not work correctly"
fi

# Check lemonade user exists
if id "lemonade" >/dev/null 2>&1; then
    echo "✓ User 'lemonade' exists"
else
    echo "⚠ User 'lemonade' does not exist"
    echo "  Will use current user instead"
    sed -i 's/^User=lemonade/#User=lemonade/' "$SERVICE_FILE"
    sed -i 's/^Group=lemonade/#Group=lemonade/' "$SERVICE_FILE"
fi

# Validate service files
echo ""
echo "Validating service files..."
systemd-analyze verify --system "$SERVICE_FILE" 2>&1 || echo "⚠ Validation warnings (may be OK)"

# Copy service files
echo ""
echo "Installing service files..."
cp "$SERVICE_FILE" /etc/systemd/system/
cp "$PROFILE_FILE" /etc/systemd/system/
echo "✓ Service files installed to /etc/systemd/system/"

# Reload systemd
echo ""
echo "Reloading systemd..."
systemctl daemon-reload
echo "✓ Systemd reloaded"

# Stop existing lemonade if running
if systemctl is-active --quiet lemonade 2>/dev/null || \
   systemctl is-active --quiet lemonade-optimized 2>/dev/null; then
    echo ""
    echo "Stopping existing Lemonade server..."
    systemctl stop lemonade 2>/dev/null || true
    systemctl stop lemonade-optimized 2>/dev/null || true
    sleep 2
    echo "✓ Existing server stopped"
fi

# Enable services
echo ""
echo "Enabling services..."
systemctl enable lemonade-optimized.service
systemctl enable lemonade-gpu-profile.service
echo "✓ Services enabled"

# Start services
echo ""
echo "Starting services..."
echo "  1. Lemonade optimized server..."
systemctl start lemonade-optimized.service
sleep 3

echo "  2. GPU power profile (high performance)..."
systemctl start lemonade-gpu-profile.service

# Wait and verify
echo ""
echo "Waiting for server to start..."
sleep 5

MAX_RETRIES=6
RETRY_COUNT=0
SERVER_READY=false

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -s http://localhost:8002/health > /dev/null 2>&1; then
        SERVER_READY=true
        break
    fi
    echo "  Checking server status... ($((RETRY_COUNT + 1))/$MAX_RETRIES)"
    sleep 3
    RETRY_COUNT=$((RETRY_COUNT + 1))
done

# Verify
echo ""
echo "========================================"
echo "Verification"
echo "========================================"

if [ "$SERVER_READY" = true ]; then
    echo "✅ Server is running and responding"
    
    # Check environment
    echo ""
    echo "Server process environment:"
    PID=$(pgrep -f "lemonade serve.*8002" | head -1)
    if [ -n "$PID" ]; then
        cat /proc/$PID/environ 2>/dev/null | tr '\0' '\n' | grep -E "RADV|HIP|HSA" | head -10 || echo "  (env vars not visible in /proc)"
    fi
    
    # Test inference
    echo ""
    echo "Testing inference..."
    RESULT=$(curl -s -X POST http://localhost:8002/v1/chat/completions \
        -H "Content-Type: application/json" \
        -d '{
            "model": "DeepSeek-R1-0528-Qwen3-8B-Q4_1",
            "messages": [{"role": "user", "content": "Hi"}],
            "max_tokens": 50
        }' 2>/dev/null | jq -r '.choices[0].message.content' 2>/dev/null | head -c 50)
    
    if [ -n "$RESULT" ]; then
        echo "✅ Inference test passed"
        echo "  Response preview: $RESULT..."
    else
        echo "⚠️ Inference test may have failed (check server logs)"
    fi
    
    # Check power profile
    echo ""
    if [ -f "/sys/class/drm/card1/device/power_dpm_force_performance_level" ]; then
        PROFILE=$(cat /sys/class/drm/card1/device/power_dpm_force_performance_level 2>/dev/null || echo "unknown")
        if [ "$PROFILE" = "high" ]; then
            echo "✅ GPU power profile: HIGH"
        else
            echo "⚠️ GPU power profile: $PROFILE (expected: high)"
        fi
    fi
    
    echo ""
    echo "========================================"
    echo "✅ Installation Complete"
    echo "========================================"
    echo ""
    echo "Systemd commands:"
    echo "  sudo systemctl status lemonade-optimized"
    echo "  sudo systemctl status lemonade-gpu-profile"
    echo "  sudo journalctl -u lemonade-optimized -f"
    echo ""
    echo "Test with:"
    echo "  python3 benchmark_amd_optimized.py"
    
else
    echo "❌ Server failed to start or is not responding"
    echo ""
    echo "Check logs:"
    echo "  sudo journalctl -u lemonade-optimized -n 50"
    echo ""
    echo "Troubleshooting:"
    echo "  1. Verify Lemonade is installed: which lemonade"
    echo "  2. Check model exists: lemonade list"
    echo "  3. Check for port conflicts: netstat -tlnp | grep 8002"
    exit 1
fi
