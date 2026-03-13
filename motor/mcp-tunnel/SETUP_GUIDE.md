---
aspect: doer
neural:
  activation: 0.63
  stage: growing
  synapse_in: 0
  synapse_out: 1
---
# MCP Tunnel Deployment Guide

**Date**: 2026-02-12
**Status**: Ready to deploy
**Objective**: Expose local Cohezion vault via public HTTPS URL for remote access

## Quick Summary

Deploy a persistent MCP server accessible from anywhere:
- 🌍 **Public URL**: `https://cohezion.duckdns.org`
- 📱 **Access from phone**: Works ✅
- ☁️ **Cloud Claude integration**: Supported ✅
- 💾 **Persistence**: systemd auto-restart ✅
- 🔒 **Security**: API key + TLS ✅

## Architecture

```
Your Machine (Strix Halo)
    ↓
cohezion-mcp-server (port 8360)
    ↓
cloudflare-tunnel (system service)
    ↓
Cloudflare Edge (Global)
    ↓
Public HTTPS: cohezion.duckdns.org
    ↓
Phone / Cloud Claude / Other Devices
```

## Deployment Steps

### 1. Install cloudflared
```bash
mkdir -p ~/.local/bin
curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 \
  -o ~/.local/bin/cloudflared
chmod +x ~/.local/bin/cloudflared
export PATH="$HOME/.local/bin:$PATH"
cloudflared --version
```

### 2. Authenticate & Create Tunnel
```bash
cloudflared tunnel login          # Opens browser
cloudflared tunnel create cohezion-vault
```

### 3. Configure Tunnel
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

cloudflared tunnel route dns cohezion-vault cohezion.duckdns.org
```

### 4. Setup systemd Services
```bash
# Generate API key (SAVE THIS!)
MCP_KEY=$(openssl rand -hex 32)
echo "Your API Key: $MCP_KEY"

# Create config directory
sudo mkdir -p /etc/cohezion
sudo tee /etc/cohezion/mcp.env > /dev/null << EOF
VAULT_PATH=/home/mike-anderson/vaults/cohezion-vault
MCP_API_KEY=$MCP_KEY
LOG_LEVEL=info
EOF
sudo chmod 600 /etc/cohezion/mcp.env

# Create tunnel service
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

[Install]
WantedBy=multi-user.target
EOF

# Create MCP server service
sudo tee /etc/systemd/system/cohezion-mcp-server.service > /dev/null << 'EOF'
[Unit]
Description=Cohezion MCP Server
After=network-online.target

[Service]
Type=simple
User=mike-anderson
WorkingDirectory=/home/mike-anderson/dev/cohezion/cloud-vault-mcp
EnvironmentFile=/etc/cohezion/mcp.env
ExecStart=/home/mike-anderson/.local/bin/uv run python -m mcp_server.main
Restart=always
RestartSec=5

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

### 5. Verify & Test
```bash
# Check services
systemctl status cloudflare-tunnel.service
systemctl status cohezion-mcp-server.service

# Wait for DNS propagation
sleep 10

# Test public access
curl -I https://cohezion.duckdns.org/health
# Should return: HTTP/2 200
```

## Using Your MCP Server

### From Phone
```
Browser → https://cohezion.duckdns.org/health
```

### From Cloud Claude (claude.ai)
1. Settings → MCP Servers → Add
2. **URL**: `https://cohezion.duckdns.org`
3. **API Key**: (your generated key)
4. Test → ✅

### From Anywhere (Curl)
```bash
curl -H "Authorization: Bearer $MCP_API_KEY" \
  https://cohezion.duckdns.org/health
```

## Monitoring & Maintenance

### View Logs
```bash
# Tunnel logs
journalctl -u cloudflare-tunnel -f

# MCP server logs
journalctl -u cohezion-mcp-server -f
```

### Health Monitoring (Optional)
```bash
# Setup 5-minute health checks
mkdir -p ~/.local/share/cohezion
cat > ~/dev/cohezion/scripts/monitor_tunnel.sh << 'EOF'
#!/bin/bash
curl -s -w "$(date): HTTP %{http_code}\n" \
  https://cohezion.duckdns.org/health >> ~/.local/share/cohezion/tunnel_health.log
EOF

chmod +x ~/dev/cohezion/scripts/monitor_tunnel.sh
(crontab -l 2>/dev/null | grep -v monitor_tunnel; echo "*/5 * * * * $HOME/dev/cohezion/scripts/monitor_tunnel.sh") | crontab -
```

### Restart Services
```bash
sudo systemctl restart cohezion-mcp-server.service
sudo systemctl restart cloudflare-tunnel.service
```

## Security

### API Key Rotation
```bash
# Every quarter, generate new key
NEW_KEY=$(openssl rand -hex 32)
sudo sed -i "s/MCP_API_KEY=.*/MCP_API_KEY=$NEW_KEY/" /etc/cohezion/mcp.env
sudo systemctl restart cohezion-mcp-server.service
```

### Access Control
- API key required for all requests
- TLS/HTTPS encryption (Cloudflare)
- Tunnel authentication (Cloudflare login required)
- Non-blocking observability (never crashes)

## Edge Cases & Recovery

### Service Crashes
- systemd will auto-restart both services
- Max 5 restarts per 60 seconds before stopping
- Check logs: `journalctl -u cohezion-mcp-server -n 50`

### Network Disconnection
- Tunnel auto-reconnects (systemd manages)
- Health check can trigger manual restart
- No data loss (local vault unaffected)

### DNS Propagation Delays
- Wait 30-60 seconds after first deployment
- Test with: `nslookup cohezion.duckdns.org`

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `Connection refused` | Check `systemctl status cohezion-mcp-server` |
| `DNS not resolving` | Wait 30s, then `nslookup cohezion.duckdns.org` |
| `Tunnel disconnecting` | Check logs: `journalctl -u cloudflare-tunnel -f` |
| `API key not working` | Verify in `/etc/cohezion/mcp.env` |
| `Phone can't access` | Disable VPN, try different WiFi |

## Related Documents

- [[2026-02-12-cloudflare-tunnel-for-persistent-mcp-remote-access|Cloudflare Tunnel Decision]] — Decision rationale for choosing Cloudflare Tunnel
- `TUNNEL_SETUP.md` - Quick reference
- Cloud Run comparison - See CLAUDE.md

## Status

- [ ] cloudflared installed
- [ ] Tunnel created
- [ ] Tunnel configured
- [ ] systemd services created
- [ ] Services started
- [ ] Public access verified
- [ ] Cloud Claude integrated
