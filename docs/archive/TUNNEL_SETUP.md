# Cloudflare Tunnel Setup for cohezion.duckdns.org

## Quick Start (Copy & Paste)

### Step 1: Install cloudflared
```bash
# Option A: Download binary directly
mkdir -p ~/.local/bin
curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o ~/.local/bin/cloudflared
chmod +x ~/.local/bin/cloudflared
export PATH="$HOME/.local/bin:$PATH"

# Verify
cloudflared --version
```

### Step 2: Authenticate with Cloudflare
```bash
cloudflared tunnel login
# Browser opens → Click "Authorize"
```

### Step 3: Create tunnel
```bash
cloudflared tunnel create cohezion-vault
# Output: Tunnel ID and credentials file
```

### Step 4: Configure tunnel
```bash
mkdir -p ~/.cloudflared
cat > ~/.cloudflared/config.yml << 'EOF'
tunnel: cohezion-vault
credentials-file: ~/.cloudflared/cohezion-vault.json

ingress:
  - hostname: cohezion.duckdns.org
    service: http://localhost:8360
  - service: http_status:404
EOF
```

### Step 5: Route DNS
```bash
cloudflared tunnel route dns cohezion-vault cohezion.duckdns.org
```

### Step 6: Setup systemd services
```bash
# Tunnel service
sudo tee /etc/systemd/system/cloudflare-tunnel.service > /dev/null << 'EOF'
[Unit]
Description=Cloudflare Tunnel (Cohezion Vault)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=mike-anderson
ExecStart=/home/mike-anderson/.local/bin/cloudflared tunnel run cohezion-vault
Restart=always
RestartSec=5
StartLimitIntervalSec=60
StartLimitBurst=5

[Install]
WantedBy=multi-user.target
EOF

# MCP server service
sudo mkdir -p /etc/cohezion
MCP_KEY=$(openssl rand -hex 32)
echo "📌 Save your API key: $MCP_KEY"

sudo tee /etc/cohezion/mcp.env > /dev/null << EOF
VAULT_PATH=/home/mike-anderson/vaults/cohezion-vault
MCP_API_KEY=$MCP_KEY
LOG_LEVEL=info
MCP_HOST=0.0.0.0
MCP_PORT=8360
EOF

sudo chmod 600 /etc/cohezion/mcp.env

sudo tee /etc/systemd/system/cohezion-mcp-server.service > /dev/null << 'EOF'
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
StandardOutput=journal
StandardError=journal
SyslogIdentifier=cohezion-mcp

[Install]
WantedBy=multi-user.target
EOF

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable cloudflare-tunnel.service cohezion-mcp-server.service
sudo systemctl start cohezion-mcp-server.service
sleep 2
sudo systemctl start cloudflare-tunnel.service
```

### Step 7: Verify deployment
```bash
# Check services
systemctl status cloudflare-tunnel.service
systemctl status cohezion-mcp-server.service

# Wait 5-10 seconds for DNS propagation
sleep 10

# Test public access
curl -I https://cohezion.duckdns.org/health

# View logs
journalctl -u cohezion-mcp-server -f
```

### Step 8: Setup health monitoring
```bash
mkdir -p ~/.local/share/cohezion
cat > ~/dev/cohezion/scripts/monitor_tunnel.sh << 'EOF'
#!/bin/bash
HEALTH_URL="https://cohezion.duckdns.org/health"
LOG_FILE="$HOME/.local/share/cohezion/tunnel_health.log"
mkdir -p "$(dirname "$LOG_FILE")"

response=$(curl -s -w "\n%{http_code}" "$HEALTH_URL" 2>&1)
http_code=$(echo "$response" | tail -1)
timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

echo "$timestamp | HTTP $http_code" >> "$LOG_FILE"

if [ "$http_code" != "200" ]; then
    echo "$timestamp | ALERT: Unhealthy" >> "$LOG_FILE"
    sudo systemctl restart cloudflare-tunnel.service 2>/dev/null || true
fi
EOF

chmod +x ~/dev/cohezion/scripts/monitor_tunnel.sh

# Add to crontab
(crontab -l 2>/dev/null | grep -v monitor_tunnel; echo "*/5 * * * * $HOME/dev/cohezion/scripts/monitor_tunnel.sh") | crontab -
```

---

## Accessing Your MCP Server

### From Phone/Browser
```
https://cohezion.duckdns.org/health
```

### From Claude.ai
1. Settings → MCP Servers (or Projects → Add Integration)
2. Add Server:
   - **Name**: `cohezion-vault`
   - **URL**: `https://cohezion.duckdns.org`
   - **API Key**: (your generated key from Step 6)
3. Test Connection → ✅

### From Curl
```bash
curl -H "Authorization: Bearer $MCP_API_KEY" \
  https://cohezion.duckdns.org/health
```

---

## Monitoring & Maintenance

### View Tunnel Logs
```bash
journalctl -u cloudflare-tunnel -f
```

### View MCP Server Logs
```bash
journalctl -u cohezion-mcp-server -f
```

### View Health Checks
```bash
tail -f ~/.local/share/cohezion/tunnel_health.log
```

### Restart Services
```bash
sudo systemctl restart cohezion-mcp-server.service
sudo systemctl restart cloudflare-tunnel.service
```

### Rotate API Key
```bash
# Generate new key
NEW_KEY=$(openssl rand -hex 32)
echo "New key: $NEW_KEY"

# Update
sudo bash -c "echo 'MCP_API_KEY=$NEW_KEY' >> /etc/cohezion/mcp.env"
sudo systemctl restart cohezion-mcp-server.service
```

---

## Troubleshooting

### DNS not resolving
```bash
nslookup cohezion.duckdns.org
# Should return tunnel IP
```

### Connection refused
```bash
# Check if MCP server is running
curl http://localhost:8360/health

# Check if tunnel is running
systemctl status cloudflare-tunnel.service
```

### Tunnel disconnecting
```bash
# View detailed logs
journalctl -u cloudflare-tunnel -n 50

# Manually reconnect
sudo systemctl restart cloudflare-tunnel.service
```

### Can't access from phone
- Wait 30 seconds for DNS propagation
- Check that your phone is not on VPN blocking cloudflare.com
- Try from different WiFi network

---

## What's Running

| Service | Port | Function |
|---------|------|----------|
| cohezion-mcp-server | 8360 (local) | Your MCP API |
| cloudflare-tunnel | N/A (tunnels to edge) | Public HTTPS proxy |
| monitor_tunnel.sh | N/A (cron every 5min) | Health checks & alerts |

---

## For Cloud Claude

Your MCP is now available to cloud.anthropic.com:
1. Add MCP server in project settings
2. URL: `https://cohezion.duckdns.org`
3. All tools from vault will be accessible

Example request from Claude.ai:
```
Use the cohezion-vault MCP to search for decisions about "authentication"
```

This will query your local vault through the tunnel!

---

## Next Steps

1. Complete all steps above
2. Test from phone
3. Add to Claude.ai project
4. Log status to vault: `vault_log_decision(...)`
5. Share tunnel URL with team if needed (keep API key secret!)
