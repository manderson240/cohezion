#!/bin/bash
# Start all MCP servers locally
# Optimized for: Cohezion Compound Engineering

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Starting MCP Server Infrastructure...${NC}"

# Check Redis
if ! docker ps | grep -q redis-mcp; then
    echo -e "${YELLOW}🔴 Redis not running, starting...${NC}"
    docker start redis-mcp || docker run -d --name redis-mcp -p 6379:6379 redis:7-alpine
fi

# Function to start a server
start_server() {
    local name=$1
    local port=$2
    local module=$3
    
    if lsof -Pi :"$port" -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo -e "${YELLOW}⚠️  $name already on $port${NC}"
        return 0
    fi
    
    echo -e "${GREEN}🔧 Starting $name on $port...${NC}"
    MCP_PORT=$port MCP_TRANSPORT=http uv run python -m "$module" > "logs/mcp_${name,,}.log" 2>&1 &
}

mkdir -p logs

start_server "Vault" 8360 "cohezion.mcp.servers.vault"
start_server "BMAD" 8361 "cohezion.mcp.servers.bmad.server"
start_server "Compound" 8379 "cohezion.mcp.compound_server"
start_server "Surreal" 8375 "cohezion.mcp.surreal_server_mcp"

echo -e "${GREEN}✨ MCP Infrastructure startup triggered!${NC}"
