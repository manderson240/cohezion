#!/bin/bash
# =============================================================================
# Cloud Vault MCP Server Startup Script
# =============================================================================
# This script starts the cloud-vault-mcp server for OpenCode vault integration.
# The server provides MCP tools for Obsidian vault access.
#
# USAGE:
#   ./scripts/start-mcp-server.sh
#
# REQUIREMENTS:
#   - cloud-vault-mcp virtual environment activated
#   - VAULT_PATH set to your Obsidian vault
#
# The server listens on http://localhost:8360
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MCP_DIR="$SCRIPT_DIR/../cloud-vault-mcp"
VAULT_PATH="${VAULT_PATH:-/home/mike-anderson/vaults/cohezion-vault}"

echo "=== Cloud Vault MCP Server ==="
echo "Vault path: $VAULT_PATH"
echo "MCP directory: $MCP_DIR"
echo ""

# Check if virtual environment exists
if [ ! -d "$MCP_DIR/.venv" ]; then
    echo "ERROR: Virtual environment not found at $MCP_DIR/.venv"
    echo "Please run: cd $MCP_DIR && python3 -m venv .venv && source .venv/bin/activate && pip install -e ."
    exit 1
fi

# Activate virtual environment
source "$MCP_DIR/.venv/bin/activate"

# Set vault path
export VAULT_PATH

# Check if server is already running
if lsof -i :8360 > /dev/null 2>&1; then
    echo "WARNING: Server may already be running on port 8360"
    echo "Checking health..."
    curl -s http://localhost:8360/health | python3 -m json.tool || true
    echo ""
    echo "If you want to restart, kill the existing process first:"
    echo "  pkill -f 'src.mcp_server.main'"
    echo ""
    echo "Starting anyway..."
fi

echo "Starting MCP server on http://localhost:8360"
echo "Press Ctrl+C to stop"
echo ""

# Start the server
cd "$MCP_DIR"
python3 -m src.mcp_server.main
