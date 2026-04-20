#!/bin/bash
# Start all MCP servers locally (without Docker)
# This script starts Redis and all MCP servers

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Starting MCP Server Infrastructure...${NC}"
echo ""

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check Redis
if ! docker ps | grep -q redis-mcp; then
    echo -e "${YELLOW}🔴 Redis not running, starting...${NC}"
    if docker ps -a | grep -q redis-mcp; then
        docker start redis-mcp
    else
        docker run -d --name redis-mcp -p 6379:6379 redis:7-alpine redis-server --appendonly yes
    fi
    echo -e "${GREEN}✅ Redis started${NC}"
    sleep 2
else
    echo -e "${GREEN}✅ Redis already running${NC}"
fi

echo ""

# Check if servers are already running
check_port() {
    lsof -Pi :"$1" -sTCP:LISTEN -t >/dev/null 2>&1
}

# Function to start a server
start_server() {
    local name=$1
    local port=$2
    local module=$3
    
    if check_port "$port"; then
        echo -e "${YELLOW}⚠️  $name MCP Server already running on port $port${NC}"
        return 0
    fi
    
    echo -e "${GREEN}🔧 Starting $name MCP Server on port $port...${NC}"
    
    # Start in background using uv
    MCP_PORT=$port uv run python -m "$module" &
    local pid=$!
    
    # Wait a moment for server to start
    sleep 3
    
    # Check if process is still running
    if kill -0 $pid 2>/dev/null; then
        echo -e "${GREEN}✅ $name MCP Server started (PID: $pid)${NC}"
        return 0
    else
        echo -e "${RED}❌ $name MCP Server failed to start${NC}"
        return 1
    fi
}

# Core Servers
echo -e "${GREEN}Starting Core Servers...${NC}"
start_server "BMAD" 8361 "cohezion.mcp.servers.bmad.server"
echo ""

start_server "Skills.sh" 8362 "cohezion.mcp.servers.skills.server"
echo ""

start_server "Doc Retriever" 8364 "cohezion.mcp.servers.doc.server"
echo ""

# Compound Engineering Servers
echo -e "${GREEN}Starting Compound Engineering Servers...${NC}"
start_server "Memory" 8366 "cohezion.mcp.servers.memory.server"
echo ""

start_server "Sequential Thinking" 8367 "cohezion.mcp.servers.sequential.server"
echo ""

start_server "Git Context" 8368 "cohezion.mcp.servers.git.server"
echo ""

start_server "Security" 8369 "cohezion.mcp.servers.security.server"
echo ""

# Physics & Report Generation
echo -e "${GREEN}Starting Physics & Report Servers...${NC}"
start_server "Plasma Physics" 8380 "cohezion.mcp.servers.plasma.server"
echo ""

start_server "Report Generation" 8381 "cohezion.mcp.servers.report.server"
echo ""

# Optional: HuggingFace (if token available)
if [ -n "$HF_TOKEN" ]; then
    echo -e "${GREEN}Starting HuggingFace MCP...${NC}"
    start_server "HuggingFace" 8365 "cohezion.mcp.servers.huggingface.server"
    echo ""
fi

# Wait for all servers to be ready
echo -e "${YELLOW}⏳ Waiting for servers to be ready...${NC}"
sleep 3

echo ""
echo -e "${GREEN}🧪 Testing servers...${NC}"

# Test function
test_server() {
    local name=$1
    local port=$2
    if curl -s http://localhost:$port/health 2>/dev/null | grep -q healthy; then
        echo -e "${GREEN}✅ $name MCP Server ($port) - ONLINE${NC}"
    else
        echo -e "${RED}❌ $name MCP Server ($port) - FAILED${NC}"
    fi
}

# Test all servers
test_server "BMAD" 8361
test_server "Skills.sh" 8362
test_server "Doc Retriever" 8364
test_server "Memory" 8366
test_server "Sequential" 8367
test_server "Git Context" 8368
test_server "Security" 8369
test_server "Plasma Physics" 8380
test_server "Report Generation" 8381

if [ -n "$HF_TOKEN" ]; then
    test_server "HuggingFace" 8365
fi

echo ""
echo -e "${GREEN}📝 Server Status:${NC}"
echo "  Core:"
echo "    BMAD:              http://localhost:8361"
echo "    Skills:            http://localhost:8362"
echo "    Doc Retriever:     http://localhost:8364"
echo ""
echo "  Compound Engineering:"
echo "    Memory:            http://localhost:8366"
echo "    Sequential:        http://localhost:8367"
echo "    Git Context:       http://localhost:8368"
echo "    Security:          http://localhost:8369"
echo ""
echo "  Physics & Reports:"
echo "    Plasma Physics:    http://localhost:8380 (HIHO & Exotic Vacuum)"
echo "    Report Generation: http://localhost:8381 (Marimo Notebooks)"
echo ""
echo "  Infrastructure:"
echo "    Redis:             localhost:6379"
echo "    SurrealDB:         localhost:8000"

echo ""
echo -e "${GREEN}🛑 To stop all servers:${NC}"
echo "  pkill -f 'cohezion.mcp.servers'"
echo "  docker stop redis-mcp"

echo ""
echo -e "${GREEN}✨ MCP Infrastructure is running!${NC}"
echo ""
echo "Quick tests:"
echo "  # BMAD help"
echo "  curl http://localhost:8361/tools/bmad_help -X POST -d '{"query": "help"}' | jq ."
echo ""
echo "  # Plasma Physics - 400 year story"
echo "  curl http://localhost:8380/tools/plasma_400_year_unification -X POST -d '{"chapter": "overview"}' | jq ."
echo ""
echo "  # Generate Marimo report"
echo "  curl http://localhost:8381/tools/report_generate -X POST -d '{"title": "Test Report", "template": "physics"}' | jq ."

# Keep script running
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop...${NC}"
wait
