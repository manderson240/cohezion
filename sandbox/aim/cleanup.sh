#!/bin/bash
# AIMO Process Cleanup Script
# Prevents zombie swarms and OOM by cleaning orphaned processes before sprint

set -e

echo "=== AIMO Process Cleanup ==="
echo "Cleaning zombie processes before sprint..."

# Clean AIMO processes
echo "Cleaning AIMO Python processes..."
ps aux | grep -i "aimo" | grep -v grep | awk '{print $2}' | xargs -r kill -9 2>/dev/null || true

# Clean Ollama processes (optional - keeps models loaded but frees children)
echo "Cleaning Ollama child processes..."
ps aux | grep -i "ollama" | grep -v grep | grep -v "server" | awk '{print $2}' | xargs -r kill -9 2>/dev/null || true

# Clean uv run processes
echo "Cleaning uv run processes..."
ps aux | grep -i "uv run" | grep -v grep | awk '{print $2}' | xargs -r kill -9 2>/dev/null || true

# Verify cleanup
echo "Verifying cleanup..."
AIMO_COUNT=$(ps aux | grep -i "aimo" | grep -v grep | wc -l)
UV_COUNT=$(ps aux | grep -i "uv run" | grep -v grep | wc -l)

if [ "$AIMO_COUNT" -eq 0 ] && [ "$UV_COUNT" -eq 0 ]; then
    echo "✅ Cleanup successful - no zombie processes"
else
    echo "⚠️  Warning: $AIMO_COUNT aimo and $UV_COUNT uv processes still running"
    echo "Manual cleanup may be required: ps aux | grep aimo | xargs kill -9"
fi

# Check system load
echo "Checking system load..."
LOAD=$(cat /proc/loadavg | awk '{print $1}')
echo "Current load: $LOAD"

if (( $(echo "$LOAD > 20" | bc -l) )); then
    echo "⚠️  Warning: System load > 20 ($LOAD)"
    echo "Consider waiting for load to decrease before starting sprint"
else
    echo "✅ System load acceptable ($LOAD)"
fi

echo "=== Cleanup Complete ==="
echo "Ready to start AIMO sprint"
