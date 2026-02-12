# MCP Tunnel Deployment Checklist

## Pre-Deployment
- [ ] Read `/home/mike-anderson/dev/cohezion/TUNNEL_SETUP.md`
- [ ] Ensure vault exists at `~/vaults/cohezion-vault/`
- [ ] Ensure MCP server code at `~/dev/cohezion/cloud-vault-mcp/`
- [ ] Have Cloudflare account (use Google OAuth at https://www.cloudflare.com)

## Installation Phase
- [ ] Install cloudflared to `~/.local/bin/cloudflared`
- [ ] Verify: `cloudflared --version`
- [ ] Authenticate: `cloudflared tunnel login` (browser opens)
- [ ] Create tunnel: `cloudflared tunnel create cohezion-vault`
- [ ] Configure tunnel: Create `~/.cloudflared/config.yml`

## DNS Setup
- [ ] Route DNS: `cloudflared tunnel route dns cohezion-vault cohezion.duckdns.org`
- [ ] Verify DNS: `nslookup cohezion.duckdns.org`

## Systemd Services
- [ ] Create `/etc/systemd/system/cloudflare-tunnel.service`
- [ ] Create `/etc/cohezion/mcp.env` (with API_KEY)
- [ ] Create `/etc/systemd/system/cohezion-mcp-server.service`
- [ ] Enable services: `sudo systemctl enable cloudflare-tunnel.service cohezion-mcp-server.service`

## Startup
- [ ] Start MCP server: `sudo systemctl start cohezion-mcp-server.service`
- [ ] Wait 2 seconds
- [ ] Start tunnel: `sudo systemctl start cloudflare-tunnel.service`
- [ ] Wait 5 seconds for DNS propagation

## Verification
- [ ] Check services running: `systemctl status cloudflare-tunnel.service`
- [ ] Check MCP server: `systemctl status cohezion-mcp-server.service`
- [ ] Test local access: `curl http://localhost:8360/health`
- [ ] Test public access: `curl https://cohezion.duckdns.org/health`
- [ ] Check logs: `journalctl -u cohezion-mcp-server -n 10`

## Cloud Claude Integration
- [ ] Log into claude.ai
- [ ] Settings → MCP Servers → Add New
- [ ] Configure:
  - Name: `cohezion-vault`
  - URL: `https://cohezion.duckdns.org`
  - API Key: (your generated key from mcp.env)
- [ ] Test connection → Should see ✅
- [ ] Try in chat: "Query the cohezion vault for recent decisions"

## Monitoring Setup
- [ ] Create `~/dev/cohezion/scripts/monitor_tunnel.sh`
- [ ] Add to crontab: `*/5 * * * * $HOME/dev/cohezion/scripts/monitor_tunnel.sh`
- [ ] Verify: `crontab -l | grep monitor_tunnel`

## Documentation
- [ ] Log decision to vault (DONE ✅)
- [ ] Update MEMORY.md (DONE ✅)
- [ ] Save API key securely (password manager)
- [ ] Share checklist with team (optional)

## Post-Deployment Testing
- [ ] Access from phone on different WiFi
- [ ] Test MCP queries from Claude.ai
- [ ] Verify health monitoring working
- [ ] Check systemd journal for errors
- [ ] Monitor DNS propagation time

## Rollback Plan (if needed)
- [ ] Stop services: `sudo systemctl stop cloudflare-tunnel.service cohezion-mcp-server.service`
- [ ] Disable services: `sudo systemctl disable cloudflare-tunnel.service cohezion-mcp-server.service`
- [ ] Delete tunnel: `cloudflared tunnel delete cohezion-vault`
- [ ] Local vault remains intact ✅

---

## Current Status

**Deployment Started**: 2026-02-12
**Document Location**: `TUNNEL_SETUP.md`
**Vault Documentation**: `~/vaults/cohezion-vault/projects/mcp-tunnel/SETUP_GUIDE.md`

**Next Action**: Follow TUNNEL_SETUP.md steps 1-8 in order.

---

## Support

If stuck, check:
1. `TUNNEL_SETUP.md` troubleshooting section
2. Service logs: `journalctl -u cohezion-mcp-server -f`
3. Tunnel logs: `journalctl -u cloudflare-tunnel -f`
4. Health log: `tail -f ~/.local/share/cohezion/tunnel_health.log`
