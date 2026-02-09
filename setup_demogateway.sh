#!/bin/bash
# DemoGateway + Claude.ai Automated Setup Script
# Automates everything except the final manual step in Claude.ai

set -e

PROJECT_DIR="/home/mike-anderson/dev/cohezion"
SERVER_PORT=5000
OLLAMA_URL="http://localhost:11434"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}════════════════════════════════════════════${NC}"
echo -e "${BLUE}  DemoGateway + Claude.ai Setup${NC}"
echo -e "${BLUE}════════════════════════════════════════════${NC}"
echo ""

# Step 1: Check if Ollama is running
echo -e "${YELLOW}[Step 1] Checking Ollama...${NC}"
if ! curl -s $OLLAMA_URL/api/tags > /dev/null 2>&1; then
    echo -e "${RED}✗ Ollama is not running!${NC}"
    echo -e "${YELLOW}Start Ollama with: ollama serve${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Ollama is running${NC}"

# Step 2: Check if required models are available
echo ""
echo -e "${YELLOW}[Step 2] Checking required models...${NC}"
MODELS=("qwen3-coder:30b" "deepseek-r1:70b" "phi3:mini")
MISSING_MODELS=()

for model in "${MODELS[@]}"; do
    if curl -s $OLLAMA_URL/api/tags | grep -q "$model"; then
        echo -e "${GREEN}✓ $model is available${NC}"
    else
        echo -e "${RED}✗ $model is missing${NC}"
        MISSING_MODELS+=("$model")
    fi
done

if [ ${#MISSING_MODELS[@]} -gt 0 ]; then
    echo ""
    echo -e "${YELLOW}Pulling missing models...${NC}"
    for model in "${MISSING_MODELS[@]}"; do
        echo -e "${YELLOW}  Pulling $model (this may take a few minutes)...${NC}"
        ollama pull "$model" || echo -e "${RED}Failed to pull $model${NC}"
    done
fi
echo ""

# Step 3: Check if ngrok is installed
echo -e "${YELLOW}[Step 3] Checking ngrok...${NC}"
if ! command -v ngrok &> /dev/null; then
    echo -e "${RED}✗ ngrok is not installed!${NC}"
    echo -e "${YELLOW}Install ngrok from: https://ngrok.com/download${NC}"
    exit 1
fi
echo -e "${GREEN}✓ ngrok is installed${NC}"
echo ""

# Step 4: Check if current port is available
echo -e "${YELLOW}[Step 4] Checking if port $SERVER_PORT is available...${NC}"
if lsof -Pi :$SERVER_PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo -e "${RED}✗ Port $SERVER_PORT is already in use!${NC}"
    echo -e "${YELLOW}Kill the process with: lsof -ti:$SERVER_PORT | xargs kill -9${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Port $SERVER_PORT is available${NC}"
echo ""

# Step 5: Start the MCP HTTP Server in background
echo -e "${YELLOW}[Step 5] Starting MCP HTTP Server...${NC}"
cd "$PROJECT_DIR"

# Kill any previous instances
pkill -f "python -m cohezion.gateway.mcp_http_server" 2>/dev/null || true
sleep 1

# Start server in background with output to file
nohup uv run python -m cohezion.gateway.mcp_http_server > /tmp/mcp_server.log 2>&1 &
MCP_PID=$!
echo -e "${GREEN}✓ MCP Server started (PID: $MCP_PID)${NC}"

# Wait for server to be ready
echo "  Waiting for server to start..."
sleep 3

# Check if server is actually running
if ! curl -s http://localhost:$SERVER_PORT/health > /dev/null 2>&1; then
    echo -e "${RED}✗ Server failed to start!${NC}"
    echo -e "${YELLOW}Check logs: cat /tmp/mcp_server.log${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Server is running on http://localhost:$SERVER_PORT${NC}"
echo ""

# Step 6: Start ngrok in background
echo -e "${YELLOW}[Step 6] Starting ngrok tunnel...${NC}"
pkill -f "ngrok http" 2>/dev/null || true
sleep 1

nohup ngrok http $SERVER_PORT > /tmp/ngrok.log 2>&1 &
NGROK_PID=$!
echo -e "${GREEN}✓ ngrok started (PID: $NGROK_PID)${NC}"

# Wait for ngrok to initialize
echo "  Waiting for ngrok to initialize..."
sleep 3

# Get the ngrok URL
NGROK_URL=$(curl -s http://localhost:4040/api/tunnels | grep -o '"public_url":"https://[^"]*' | cut -d'"' -f4 | head -1)

if [ -z "$NGROK_URL" ]; then
    echo -e "${RED}✗ Failed to get ngrok URL!${NC}"
    echo -e "${YELLOW}Check ngrok logs: cat /tmp/ngrok.log${NC}"
    exit 1
fi

echo -e "${GREEN}✓ ngrok tunnel established${NC}"
echo ""

# Step 7: Display connection information
echo -e "${GREEN}════════════════════════════════════════════${NC}"
echo -e "${GREEN}  ✓ Setup Complete!${NC}"
echo -e "${GREEN}════════════════════════════════════════════${NC}"
echo ""
echo -e "${BLUE}MCP Server Information:${NC}"
echo -e "  Local URL:  ${YELLOW}http://localhost:$SERVER_PORT${NC}"
echo -e "  Public URL: ${YELLOW}$NGROK_URL${NC}"
echo ""
echo -e "${BLUE}Servers Running:${NC}"
echo -e "  MCP HTTP Server: ${GREEN}Running (PID $MCP_PID)${NC}"
echo -e "  ngrok Tunnel:    ${GREEN}Running (PID $NGROK_PID)${NC}"
echo ""

# Step 8: Save configuration to file
CONFIG_FILE="/tmp/demogateway_config.txt"
cat > "$CONFIG_FILE" << EOF
# DemoGateway Configuration
MCP_SERVER_LOCAL=http://localhost:$SERVER_PORT
MCP_SERVER_PUBLIC=$NGROK_URL
MCP_SERVER_SSE=$NGROK_URL/sse
MCP_PID=$MCP_PID
NGROK_PID=$NGROK_PID

# Use these values in Claude.ai custom connector:
# Name: ngrok AI Gateway
# Remote MCP server URL: $NGROK_URL/sse
# OAuth Client ID: (leave blank)
# OAuth Client Secret: (leave blank)
EOF

echo -e "${BLUE}Configuration saved to:${NC}"
echo -e "  ${YELLOW}$CONFIG_FILE${NC}"
echo ""

# Step 9: Manual Claude.ai instructions
echo -e "${YELLOW}════════════════════════════════════════════${NC}"
echo -e "${YELLOW}  Manual Step: Add Custom Connector to Claude.ai${NC}"
echo -e "${YELLOW}════════════════════════════════════════════${NC}"
echo ""
echo -e "${BLUE}1. Open Claude.ai:${NC}"
echo -e "   https://claude.ai"
echo ""
echo -e "${BLUE}2. Go to Settings → Custom Connectors${NC}"
echo ""
echo -e "${BLUE}3. Click \"Add Custom Connector\"${NC}"
echo ""
echo -e "${BLUE}4. Fill in the form:${NC}"
echo -e "   Name: ${YELLOW}ngrok AI Gateway${NC}"
echo -e "   Remote MCP server URL: ${YELLOW}$NGROK_URL/sse${NC}"
echo -e "   OAuth Client ID: ${YELLOW}(leave blank)${NC}"
echo -e "   OAuth Client Secret: ${YELLOW}(leave blank)${NC}"
echo ""
echo -e "${BLUE}5. Click \"Save Connector\"${NC}"
echo ""
echo -e "${GREEN}✓ Then come back to Claude and use the connector!${NC}"
echo ""

# Step 10: Test the connector
echo -e "${YELLOW}[Step 8] Testing MCP Server...${NC}"
TOOLS=$(curl -s http://localhost:$SERVER_PORT/tools)
if echo "$TOOLS" | grep -q "generate"; then
    echo -e "${GREEN}✓ MCP server is responding to tool requests${NC}"
    echo -e "  Available tools: generate, get_metrics, get_providers, configure_gateway, cost_estimate"
else
    echo -e "${YELLOW}⚠ Could not verify tools, but server is running${NC}"
fi
echo ""

# Step 11: Cleanup instructions
echo -e "${BLUE}To stop the servers later:${NC}"
echo -e "  kill $MCP_PID  # Stop MCP Server"
echo -e "  kill $NGROK_PID  # Stop ngrok tunnel"
echo ""
echo -e "${BLUE}Or use this command to stop both:${NC}"
echo -e "  ${YELLOW}pkill -f 'python -m cohezion.gateway.mcp_http_server'; pkill -f 'ngrok http'${NC}"
echo ""

# Step 12: Keep running
echo -e "${GREEN}════════════════════════════════════════════${NC}"
echo -e "${GREEN}  Servers are running! Press Ctrl+C to stop.${NC}"
echo -e "${GREEN}════════════════════════════════════════════${NC}"
echo ""

# Display logs
echo -e "${YELLOW}MCP Server Log:${NC}"
tail -f /tmp/mcp_server.log &
TAIL_PID=$!

# Trap to cleanup on exit
trap "kill $MCP_PID $NGROK_PID $TAIL_PID 2>/dev/null; echo -e '\n${YELLOW}Servers stopped.${NC}'; exit 0" SIGINT SIGTERM

# Keep script running
wait
