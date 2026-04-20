#!/bin/bash
# Start Cohezion MCP Fleet Manager
# Optimized for local AMD silicon with ROCm 6.2

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Starting Cohezion MCP Fleet...${NC}"

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Ensure Redis is running (required for BMAD & Memory)
if ! docker ps | grep -q redis-mcp; then
    echo -e "${YELLOW}🔴 Redis not running, starting...${NC}"
    docker run -d --name redis-mcp -p 6379:6379 redis:7-alpine redis-server --appendonly yes 2>/dev/null || docker start redis-mcp
fi

# Hardware optimizations
export TORCH_ROCM_ARCH="gfx1100"
export HSA_OVERRIDE_GFX_VERSION="11.0.0"
export PYTHONPATH="$SCRIPT_DIR/src"

# Define servers to start (HTTP mode for multi-server parallel access)
SERVERS=("bmad" "coherence" "skills" "research" "surreal" "swarm" "knowledge")
PORTS=(8361 8363 8362 8365 8367 8368 8364) # Unified ports

for i in "${!SERVERS[@]}"; do
    SERVER=${SERVERS[$i]}
    PORT=${PORTS[$i]}
    echo -e "${GREEN}🔧 Starting $SERVER on port $PORT...${NC}"
    "$SCRIPT_DIR/.venv/bin/python" -m cohezion.mcp.fleet "$SERVER" --transport http --port "$PORT" &
done

echo ""
echo -e "${GREEN}✨ MCP Fleet is launching in the background.${NC}"
echo -e "${YELLOW}Use 'pkill -f cohezion.mcp.fleet' to stop.${NC}"
