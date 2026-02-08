#!/usr/bin/env bash
set -euo pipefail

# Cloud Vault MCP Server — One-command setup
# Usage: ./setup.sh [--dev]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VAULT_DIR="${SCRIPT_DIR}/vault"

echo "=== Cloud Vault MCP Server Setup ==="
echo ""

# ── 1. Environment file ───────────────────────────────────────────────

if [ ! -f "${SCRIPT_DIR}/.env" ]; then
    echo "Creating .env from .env.example..."
    cp "${SCRIPT_DIR}/.env.example" "${SCRIPT_DIR}/.env"

    # Generate API key
    API_KEY=$(python3 -c "import hashlib, os; print(hashlib.sha256(os.urandom(32)).hexdigest())")
    sed -i "s/^MCP_API_KEY=$/MCP_API_KEY=${API_KEY}/" "${SCRIPT_DIR}/.env"

    echo "Generated API key: ${API_KEY}"
    echo "IMPORTANT: Save this key — you'll need it to connect clients."
    echo ""
else
    echo ".env already exists, skipping."
fi

# ── 2. Initialize vault as Git repo ──────────────────────────────────

if [ ! -d "${VAULT_DIR}/.git" ]; then
    echo "Initializing vault as Git repository..."
    cd "${VAULT_DIR}"
    git init
    git add -A
    git commit -m "Initial vault structure"
    cd "${SCRIPT_DIR}"
    echo "Vault Git repo initialized."
else
    echo "Vault Git repo already exists, skipping."
fi

# ── 3. Create nginx cert directory ───────────────────────────────────

mkdir -p "${SCRIPT_DIR}/deploy/nginx/certs"

# ── 4. Dev mode or Docker mode ───────────────────────────────────────

if [ "${1:-}" = "--dev" ]; then
    echo ""
    echo "=== Development Mode ==="
    echo "Installing Python package in editable mode..."

    cd "${SCRIPT_DIR}"
    pip install -e ".[dev]" 2>/dev/null || pip install -e . 2>/dev/null

    echo ""
    echo "To start the server locally:"
    echo "  export VAULT_PATH=${VAULT_DIR}"
    echo "  source .env"
    echo "  export MCP_API_KEY MCP_PORT"
    echo "  cloud-vault-mcp"
    echo ""
    echo "Or run directly:"
    echo "  VAULT_PATH=${VAULT_DIR} MCP_API_KEY=\$(grep MCP_API_KEY .env | cut -d= -f2) python -m mcp_server.main"
else
    echo ""
    echo "=== Docker Mode ==="
    echo "Building and starting containers..."

    cd "${SCRIPT_DIR}"
    docker compose build
    docker compose up -d mcp-server

    echo ""
    echo "MCP server is running on port $(grep MCP_PORT .env 2>/dev/null | cut -d= -f2 || echo 8360)"
    echo ""
    echo "To also start nginx (requires TLS certs in deploy/nginx/certs/):"
    echo "  docker compose up -d nginx"
    echo ""
    echo "To start git-sync:"
    echo "  docker compose up -d git-sync"
fi

echo ""
echo "=== Claude Code Configuration ==="
echo ""
echo "Add to your Claude Code MCP config (~/.claude/mcp.json or project .mcp.json):"
echo ""
echo '  {'
echo '    "mcpServers": {'
echo '      "cloud-vault": {'
echo '        "type": "streamable-http",'
echo '        "url": "http://localhost:8360/mcp",'
echo '        "headers": {'
echo "          \"Authorization\": \"Bearer $(grep MCP_API_KEY "${SCRIPT_DIR}/.env" 2>/dev/null | cut -d= -f2 || echo '<YOUR_API_KEY>')\""
echo '        }'
echo '      }'
echo '    }'
echo '  }'
echo ""
echo "=== Setup Complete ==="
