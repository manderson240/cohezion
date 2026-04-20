# Cloud Claude Vault Access - Quick Start

**TL;DR**: SSH tunnel for secure, stable access. GitHub for backup.

## For Local Machine Operator

### 1. Generate SSH Access (3 min)

```bash
cd /home/mike-anderson/dev/cohezion/cloud-vault-mcp
chmod +x scripts/setup-cloud-access.sh
./scripts/setup-cloud-access.sh
```

This will:
- Generate SSH key (`~/.ssh/id_cloud_claude`)
- Add to authorized_keys with port restrictions
- Set up GitHub backup (optional)
- Display instructions for cloud machine

### 2. Share With Cloud Machine Operator

```
Private key path: /home/mike-anderson/.ssh/id_cloud_claude
Host: <Your IP or hostname>
Local SSH user: mike-anderson
```

**IMPORTANT**: Transfer private key securely (not via email/Slack)

## For Cloud Machine Operator

### 1. Store SSH Key (2 min)

```bash
mkdir -p ~/.ssh/cohezion
chmod 700 ~/.ssh/cohezion

# Copy id_cloud_claude to ~/.ssh/cohezion/ (securely)
chmod 600 ~/.ssh/cohezion/id_cloud_claude
```

### 2. Configure SSH (2 min)

Create `~/.ssh/config`:

```
Host vault-tunnel
    HostName <LOCAL_MACHINE_IP>
    User mike-anderson
    IdentityFile ~/.ssh/cohezion/id_cloud_claude
    StrictHostKeyChecking accept-new
    LocalForward 127.0.0.1:8360 127.0.0.1:8360
    ServerAliveInterval 60
    ServerAliveCountMax 10
    ExitOnForwardFailure yes
```

### 3. Test Connection (1 min)

```bash
# Start tunnel
ssh -N -f vault-tunnel

# Verify
curl http://127.0.0.1:8360/health

# Should return: OK or health info
```

### 4. Configure Claude Code (1 min)

Update `~/.claude/mcp.json`:

```json
{
  "mcpServers": {
    "cohezion-vault": {
      "type": "http",
      "url": "http://127.0.0.1:8360/mcp",
      "headers": {
        "Authorization": "Bearer a712027605bbd33068da5462bbcc18d90f844df23f948f124908fa726d678263"
      }
    }
  }
}
```

### 5. Use in Claude Code

```
I need to search the vault for design decisions.
Use vault_search to find notes about token optimization.
```

## Maintenance

### Health Check (Local Machine)

```bash
# Is vault running?
curl http://localhost:8360/health

# Is backup current?
cd /home/mike-anderson/vaults/cohezion-vault
git log -1 --oneline  # Should show recent "auto-sync" commits

# Are there uncommitted changes?
git status
```

### Token Rotation (Every 90 Days)

```bash
# Local machine
cd /home/mike-anderson/dev/cohezion/cloud-vault-mcp
./scripts/rotate-token.sh

# Cloud machine: Update ~/.claude/mcp.json with new token
```

### Tunnel Down? (Cloud Machine)

```bash
# Kill old tunnel
pkill -f "ssh.*vault-tunnel"

# Restart
ssh -N -f vault-tunnel

# Verify
curl http://127.0.0.1:8360/health
```

## Verification

**Local Machine**: Check everything works

```bash
chmod +x scripts/verify-tunnel.sh
./scripts/verify-tunnel.sh  # Just checks SSH setup, not tunnel
```

**Cloud Machine**: Full connection test

```bash
chmod +x scripts/verify-tunnel.sh
./scripts/verify-tunnel.sh
```

Expected output:
```
✓ SSH private key found
✓ SSH config has vault-tunnel entry
✓ SSH tunnel established
✓ Port 8360 is now accessible
✓ MCP server health endpoint responsive
✓ MCP server is responding to authenticated requests
✓ Vault tools are available
✓ Claude Code MCP config exists
✓ cohezion-vault MCP server configured

✓ All checks passed!
```

## Troubleshooting

### "Connection refused" on 8360

```bash
# Check tunnel is running
ps aux | grep "ssh.*vault-tunnel"

# If not, restart
ssh -N -f vault-tunnel

# Verify
netstat -tuln | grep 8360
```

### "Unauthorized" error

```bash
# Check token matches
grep "MCP_API_KEY" ~/.env          # Local
grep "Authorization" ~/.claude/mcp.json  # Cloud

# Should be identical
```

### SSH key permission denied

```bash
# Check permissions
ls -la ~/.ssh/cohezion/id_cloud_claude
# Should show: -rw------- (600)

chmod 600 ~/.ssh/cohezion/id_cloud_claude
chmod 700 ~/.ssh/cohezion
chmod 700 ~/.ssh
```

### Tunnel keeps disconnecting

Set up health check script:

```bash
# Cloud machine
chmod +x ~/.local/bin/vault-tunnel-health.sh

# Run in background
tmux new-session -d -s vault-health ~/.local/bin/vault-tunnel-health.sh

# Check status
tmux capture-pane -t vault-health -p
```

## Architecture Summary

```
Cloud Claude ─── SSH Tunnel ─── Local SSH Server
                 (Port 8360)
                      ↓
                 MCP Server:8360
                      ↓
                 Vault Directory
                      ↓
                 Git Auto-Sync
                      ↓
                 GitHub Backup
```

## Security

- **Transport**: SSH with ed25519 keys (256-bit elliptic curve)
- **Authentication**: Bearer token (SHA256 hash)
- **Authorization**: SSH key locked to port 8360 only
- **Audit**: GitHub tracks every change
- **Monitoring**: Health checks every 30 seconds with auto-reconnect

## Files

| File | Purpose |
|------|---------|
| `CLOUD_CLAUDE_ACCESS.md` | Complete technical reference |
| `CLOUD_ACCESS_QUICKSTART.md` | This file - quick start |
| `scripts/setup-cloud-access.sh` | Automated setup for local machine |
| `scripts/verify-tunnel.sh` | Test connection and config |
| `scripts/rotate-token.sh` | Rotate bearer token |

## Support

- **General**: See `CLOUD_CLAUDE_ACCESS.md` (detailed guide)
- **Errors**: Check TROUBLESHOOTING.md
- **MCP Tools**: See `MCP_CLAUDE_CODE_INTEGRATION.md`

## Next: Enable in Claude Code

After tunnel is working and verified, test in Claude Code:

```
Tell me: can you access the vault?
Use vault_search("test") to search for any notes.
```

If that works, you're all set!
