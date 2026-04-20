#!/bin/bash
set -e

echo "🚀 Deploying MCP Tunnel..."

# 1. Install cloudflared
if ! command -v cloudflared &> /dev/null; then
    echo "Installing cloudflared..."
    curl -L --output /tmp/cloudflared.tgz https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.tgz
    tar -xzf /tmp/cloudflared.tgz
    sudo mv cloudflared /usr/local/bin/
    rm /tmp/cloudflared.tgz
    echo "✅ cloudflared installed"
else
    echo "✅ cloudflared already installed"
fi

# 2. Auth (interactive)
echo ""
echo "Step 1: Authenticating with Cloudflare..."
echo "(A browser window will open. Click 'Authorize' to approve tunnel creation)"
cloudflared tunnel login

# 3. Create tunnel
echo ""
echo "Step 2: Creating tunnel 'cohezion-vault'..."
cloudflared tunnel create cohezion-vault 2>/dev/null || echo "✅ Tunnel already exists"

# 4. Configure
echo "Step 3: Configuring tunnel..."
mkdir -p ~/.cloudflared
cat > ~/.cloudflared/config.yml << 'CONFIG'
tunnel: cohezion-vault
credentials-file: ~/.cloudflared/cohezion-vault.json

ingress:
  - hostname: cohezion.duckdns.org
    service: http://localhost:8360
  - service: http_status:404
CONFIG
echo "✅ Config created"

# 5. Route DNS
echo "Step 4: Routing DNS..."
cloudflared tunnel route dns cohezion-vault cohezion.duckdns.org
echo "✅ DNS routed: cohezion.duckdns.org → tunnel"

# 6. Setup systemd service for tunnel
echo "Step 5: Setting up systemd service for tunnel..."
sudo tee /etc/systemd/system/cloudflare-tunnel.service > /dev/null << 'SERVICE'
[Unit]
Description=Cloudflare Tunnel (Cohezion Vault)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=mike-anderson
ExecStart=/usr/local/bin/cloudflared tunnel run cohezion-vault
Restart=always
RestartSec=5
StartLimitIntervalSec=60
StartLimitBurst=5
KillMode=mixed
KillSignal=SIGTERM
TimeoutStopSec=10

[Install]
WantedBy=multi-user.target
SERVICE

# 7. Setup systemd service for MCP server
echo "Step 6: Setting up systemd service for MCP server..."
MCP_API_KEY=$(openssl rand -hex 32)

sudo mkdir -p /etc/cohezion
sudo tee /etc/cohezion/mcp.env > /dev/null << ENV
VAULT_PATH=/home/mike-anderson/vaults/cohezion-vault
MCP_API_KEY=$MCP_API_KEY
LOG_LEVEL=info
MCP_HOST=0.0.0.0
MCP_PORT=8360
ENV

sudo chmod 600 /etc/cohezion/mcp.env

sudo tee /etc/systemd/system/cohezion-mcp-server.service > /dev/null << 'SERVICE'
[Unit]
Description=Cohezion MCP Server (Persistent)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=mike-anderson
WorkingDirectory=/home/mike-anderson/dev/cohezion/cloud-vault-mcp
EnvironmentFile=/etc/cohezion/mcp.env

ExecStart=/home/mike-anderson/.local/bin/uv run python -m mcp_server.main

Restart=always
RestartSec=5
StartLimitIntervalSec=60
StartLimitBurst=3

StandardOutput=journal
StandardError=journal
SyslogIdentifier=cohezion-mcp

[Install]
WantedBy=multi-user.target
SERVICE

echo "✅ Systemd services created"

# 8. Reload and enable services
echo "Step 7: Enabling systemd services..."
sudo systemctl daemon-reload
sudo systemctl enable cloudflare-tunnel.service cohezion-mcp-server.service
echo "✅ Services enabled"

# 9. Start services
echo "Step 8: Starting services..."
sudo systemctl start cohezion-mcp-server.service
sleep 2
sudo systemctl start cloudflare-tunnel.service
sleep 3

# 10. Setup monitoring script
echo "Step 9: Setting up health monitoring..."
mkdir -p ~/.local/share/cohezion
cat > ~/dev/cohezion/scripts/monitor_tunnel.sh << 'MONITOR'
#!/bin/bash
HEALTH_URL="https://cohezion.duckdns.org/health"
LOG_FILE="$HOME/.local/share/cohezion/tunnel_health.log"
mkdir -p "$(dirname "$LOG_FILE")"

check_health() {
    local response=$(curl -s -w "\n%{http_code}" "$HEALTH_URL" 2>&1)
    local http_code=$(echo "$response" | tail -1)
    local timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

    echo "$timestamp | HTTP $http_code" >> "$LOG_FILE"

    if [ "$http_code" != "200" ]; then
        echo "$timestamp | ALERT: Tunnel unhealthy (HTTP $http_code)" >> "$LOG_FILE"
        sudo systemctl restart cloudflare-tunnel.service 2>/dev/null || true
    fi
}

check_health
MONITOR

chmod +x ~/dev/cohezion/scripts/monitor_tunnel.sh

# Add to crontab
(crontab -l 2>/dev/null | grep -v "monitor_tunnel.sh"; echo "*/5 * * * * $HOME/dev/cohezion/scripts/monitor_tunnel.sh") | crontab -
echo "✅ Health monitoring enabled (every 5 minutes)"

# 11. Verification
echo ""
echo "=========================================="
echo "✅ DEPLOYMENT COMPLETE"
echo "=========================================="
echo ""
echo "📍 Public URL: https://cohezion.duckdns.org"
echo "🔑 API Key: $MCP_API_KEY"
echo ""
echo "📋 Save this API key! You'll need it to configure Claude.ai"
echo ""
echo "Status checks:"
systemctl status cloudflare-tunnel.service --no-pager | head -3
echo ""
systemctl status cohezion-mcp-server.service --no-pager | head -3
echo ""
echo "Testing public access (wait 5 seconds for DNS to propagate)..."
sleep 5
if curl -s https://cohezion.duckdns.org/health > /dev/null 2>&1; then
    echo "✅ PUBLIC ACCESS WORKING"
else
    echo "⏳ DNS may still be propagating, check in 30 seconds:"
    echo "   curl https://cohezion.duckdns.org/health"
fi

echo ""
echo "📚 Documentation:"
echo "  - View tunnel logs:  systemctl status cloudflare-tunnel.service"
echo "  - View MCP logs:     journalctl -u cohezion-mcp-server -f"
echo "  - Monitor health:    tail -f ~/.local/share/cohezion/tunnel_health.log"
echo "  - Restart services:  sudo systemctl restart cohezion-mcp-server cloudflare-tunnel"
