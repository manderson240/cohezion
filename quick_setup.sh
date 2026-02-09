#!/bin/bash
# Quick Setup - Just run this and copy the output to Claude.ai

cd /home/mike-anderson/dev/cohezion

# Kill any existing processes
pkill -f "python -m cohezion.gateway.mcp_http_server" 2>/dev/null || true
pkill -f "ngrok http" 2>/dev/null || true
sleep 1

# Start MCP server
echo "Starting MCP server..."
nohup uv run python -m cohezion.gateway.mcp_http_server > /tmp/mcp.log 2>&1 &
MCP_PID=$!
sleep 3

# Start ngrok
echo "Starting ngrok tunnel..."
nohup ngrok http 5000 > /tmp/ngrok.log 2>&1 &
sleep 3

# Get ngrok URL
NGROK_URL=$(curl -s http://localhost:4040/api/tunnels | grep -o '"public_url":"https://[^"]*' | cut -d'"' -f4 | head -1)

# Output what you need for Claude.ai
echo ""
echo "════════════════════════════════════════════"
echo "ADD THIS TO CLAUDE.AI:"
echo "════════════════════════════════════════════"
echo ""
echo "Name: ngrok AI Gateway"
echo "URL: $NGROK_URL/sse"
echo "OAuth ID: (leave blank)"
echo "OAuth Secret: (leave blank)"
echo ""
echo "════════════════════════════════════════════"
echo "Servers running (Press Ctrl+C to stop)"
echo "════════════════════════════════════════════"

# Keep running
trap "kill $MCP_PID 2>/dev/null; pkill -f 'ngrok http' 2>/dev/null; exit 0" SIGINT
tail -f /tmp/mcp.log
