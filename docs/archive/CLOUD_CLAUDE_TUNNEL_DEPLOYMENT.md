# Cloud Claude Tunnel Deployment Handoff

**Status**: 50% complete - cloudflared installed, awaiting cloud-based steps
**Machine**: Strix Halo (always-on)
**Goal**: Complete Cloudflare Tunnel setup for persistent MCP access

---

## What's Already Done

✅ cloudflared binary installed at `~/.local/bin/cloudflared` (version 2026.2.0)
✅ All deployment scripts created and committed to git
✅ Architecture designed and documented
✅ Systemd service templates prepared

---

## What Cloud Claude Needs to Do

### Step 1: Authenticate with Cloudflare (INTERACTIVE - Only Local Claude Can Do)

**Local Claude must run this command on the Strix Halo machine:**
```bash
~/.local/bin/cloudflared tunnel login
```

This opens a browser to authorize tunnel creation. Local Claude clicks "Authorize" and saves credentials.

**After Local Claude completes auth**, continue with steps below.

---

## Steps 2-8: Cloud Claude Can Execute Autonomously

Once local cloudflared authentication is complete, cloud Claude can execute all remaining steps without user interaction.

### Step 2: Create Tunnel
```bash
~/.local/bin/cloudflared tunnel create cohezion-vault
# Output shows: Tunnel ID and credentials file path
```

### Step 3: Configure Tunnel
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

### Step 4: Route DNS
```bash
~/.local/bin/cloudflared tunnel route dns cohezion-vault cohezion.duckdns.org
```

### Step 5: Create Config Directory & Generate API Key
```bash
MCP_KEY=$(openssl rand -hex 32)
echo "=== SAVE THIS API KEY ==="
echo "$MCP_KEY"
echo "=========================="

sudo mkdir -p /etc/cohezion
sudo tee /etc/cohezion/mcp.env > /dev/null << EOF
VAULT_PATH=/home/mike-anderson/vaults/cohezion-vault
MCP_API_KEY=$MCP_KEY
LOG_LEVEL=info
MCP_HOST=0.0.0.0
MCP_PORT=8360
EOF

sudo chmod 600 /etc/cohezion/mcp.env
```

### Step 6: Create Systemd Services
```bash
# Cloudflare Tunnel Service
sudo tee /etc/systemd/system/cloudflare-tunnel.service > /dev/null << 'SERVICE'
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
SERVICE

# MCP Server Service
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
StandardOutput=journal
StandardError=journal
SyslogIdentifier=cohezion-mcp

[Install]
WantedBy=multi-user.target
SERVICE

sudo systemctl daemon-reload
sudo systemctl enable cloudflare-tunnel.service cohezion-mcp-server.service
```

### Step 7: Start Services
```bash
echo "Starting MCP server..."
sudo systemctl start cohezion-mcp-server.service
sleep 2

echo "Starting tunnel..."
sudo systemctl start cloudflare-tunnel.service
sleep 5

echo "Checking service status..."
systemctl status cloudflare-tunnel.service
systemctl status cohezion-mcp-server.service
```

### Step 8: Verification
```bash
echo "Waiting 10 seconds for DNS propagation..."
sleep 10

echo "Testing local access..."
curl -v http://localhost:8360/health

echo "Testing public access..."
curl -v https://cohezion.duckdns.org/health

echo "Checking logs..."
journalctl -u cohezion-mcp-server -n 5
journalctl -u cloudflare-tunnel -n 5
```

### Step 9: Setup Health Monitoring (Optional)
```bash
mkdir -p ~/.local/share/cohezion
cat > ~/dev/cohezion/scripts/monitor_tunnel.sh << 'MONITOR'
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
MONITOR

chmod +x ~/dev/cohezion/scripts/monitor_tunnel.sh

# Add to crontab
(crontab -l 2>/dev/null | grep -v monitor_tunnel; echo "*/5 * * * * $HOME/dev/cohezion/scripts/monitor_tunnel.sh") | crontab -
```

---

## Critical Information for Cloud Claude

### SSH Connection Details
```
Host: Strix Halo
User: mike-anderson
Key: Use SSH key authentication (if available)
```

### Paths
- Vault: `/home/mike-anderson/vaults/cohezion-vault/`
- MCP Server: `/home/mike-anderson/dev/cohezion/cloud-vault-mcp/`
- Cloudflared: `/home/mike-anderson/.local/bin/cloudflared`
- Scripts: `/home/mike-anderson/dev/cohezion/scripts/`

### Expected Results
- MCP Server on `http://localhost:8360` (local only)
- Public HTTPS URL: `https://cohezion.duckdns.org`
- HTTP 200 on health endpoints
- Systemd services auto-restart on crash
- Health checks every 5 minutes via cron

### Troubleshooting
If any step fails:
1. Check service logs: `journalctl -u cohezion-mcp-server -f`
2. Check tunnel logs: `journalctl -u cloudflare-tunnel -f`
3. Verify DNS: `nslookup cohezion.duckdns.org`
4. Test local MCP: `curl http://localhost:8360/health`

---

## Local Claude: Critical Pre-Requisite

Before cloud Claude runs any of the above steps, **you must complete Step 1**:

```bash
~/.local/bin/cloudflared tunnel login
```

This is the ONLY interactive step that requires local authentication. Once this is done, all other steps are fully automated.

**Share the message "Cloudflare auth complete" with cloud Claude after you finish Step 1.**

---

## For Cloud Claude: Execution Order

1. Wait for message from local Claude: "Cloudflare auth complete"
2. Execute Steps 2-9 in order (can be done all at once or separately)
3. Verify DNS propagation (may take 30-60 seconds)
4. Test public access from multiple locations if possible
5. Commit completion to git with summary
6. Report final API key to local Claude (for cloud claude.ai setup)

---

## Integration with Cloud Claude.ai

After deployment, local Claude should:
1. Log into claude.ai
2. Add MCP server:
   - URL: `https://cohezion.duckdns.org`
   - API Key: (from `/etc/cohezion/mcp.env`)
3. Test connection in claude.ai
4. Use vault queries from cloud claude

---

## Reference Files in Repo

- `TUNNEL_SETUP.md` - Detailed guide
- `TUNNEL_DEPLOYMENT_CHECKLIST.md` - Verification checklist
- `SESSION_56_TUNNEL_DEPLOYMENT_SUMMARY.md` - Complete overview
- `scripts/deploy_tunnel.sh` - Alternative automated script

---

## Success Criteria

- [ ] cloudflared tunnel login completed (local only)
- [ ] Tunnel created: `cohezion-vault`
- [ ] DNS routed: `cohezion.duckdns.org`
- [ ] Systemd services created and enabled
- [ ] Services started and stable
- [ ] Public access verified (HTTP 200)
- [ ] Health monitoring configured
- [ ] Logs show no errors
- [ ] Ready for cloud claude.ai integration

---

**Cloud Claude: You can execute all steps 2-9 autonomously once local Claude completes authentication.**

**Local Claude: Start with `~/.local/bin/cloudflared tunnel login` → Then share "Cloudflare auth complete" with cloud Claude.**
