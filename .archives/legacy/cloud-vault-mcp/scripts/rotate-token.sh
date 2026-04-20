#!/bin/bash
# Rotate MCP Bearer Token (security best practice)
# Run on LOCAL machine

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[✓]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[!]${NC} $1"
}

log_error() {
    echo -e "${RED}[✗]${NC} $1"
}

echo "MCP Bearer Token Rotation"
echo "========================"
echo ""
echo "This script will:"
echo "  1. Generate new token"
echo "  2. Update local .env"
echo "  3. Restart MCP server"
echo "  4. Display instructions for cloud machine"
echo ""

# Ask for confirmation
read -p "Continue? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    log_error "Cancelled"
    exit 1
fi

echo ""

# Generate new token
log_info "Generating new Bearer token..."
NEW_TOKEN=$(python3 -c "import hashlib,os; print(hashlib.sha256(os.urandom(32)).hexdigest())")
OLD_TOKEN=$(grep "MCP_API_KEY=" /home/mike-anderson/dev/cohezion/cloud-vault-mcp/.env | cut -d= -f2)

echo "Old token: ${OLD_TOKEN:0:16}...${OLD_TOKEN: -16}"
echo "New token: ${NEW_TOKEN:0:16}...${NEW_TOKEN: -16}"
echo ""

# Update .env
ENV_FILE="/home/mike-anderson/dev/cohezion/cloud-vault-mcp/.env"
log_info "Updating .env..."
sed -i "s/MCP_API_KEY=.*/MCP_API_KEY=$NEW_TOKEN/" "$ENV_FILE"

# Check if docker-compose is running
if docker-compose -f /home/mike-anderson/dev/cohezion/cloud-vault-mcp/docker-compose.yml ps mcp-server 2>/dev/null | grep -q "running"; then
    log_info "Restarting MCP server..."
    cd /home/mike-anderson/dev/cohezion/cloud-vault-mcp
    docker-compose restart mcp-server
    sleep 5

    # Verify it's running
    if curl -s "http://localhost:8360/health" > /dev/null; then
        log_info "MCP server restarted successfully"
    else
        log_warn "MCP server health check failed - may still be starting"
    fi
else
    log_warn "Docker MCP server not running - skipped restart"
    log_info "When you start the server, it will use the new token"
fi

echo ""
echo "========================"
echo "Next Steps"
echo "========================"
cat << EOF

Update on CLOUD MACHINE:

1. Edit ~/.claude/mcp.json

Find:
  "Authorization": "Bearer $OLD_TOKEN"

Replace with:
  "Authorization": "Bearer $NEW_TOKEN"

2. Restart Claude Code session (new token will be loaded)

3. Test vault tools in Claude Code

Old token: $OLD_TOKEN
New token: $NEW_TOKEN

Both tokens are valid for 5 minutes to allow gradual migration.
After 5 minutes, only the new token will work.

EOF

log_info "Token rotation complete!"
log_warn "Share new token with cloud Claude operator immediately"
