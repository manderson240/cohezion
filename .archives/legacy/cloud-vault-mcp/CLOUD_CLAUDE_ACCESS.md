# Cloud Claude Access to Cohezion Vault - Secure Setup

**Objective**: Enable cloud Claude to access vault server securely and stably via SSH tunnel + automated failover.

## Architecture

```
Cloud Claude Session
    ↓
SSH Tunnel (Port 8360 → localhost:8360)
    ↓
Local Machine (SSH Server)
    ↓
MCP Server (8360)
    ↓
Vault Data (/home/mike-anderson/vaults/cohezion-vault)
    ↓
Git Sync Daemon (auto-backup to GitHub)
```

## Prerequisites

- Local machine with SSH server running
- GitHub repo for vault backup (private recommended)
- OpenSSH client on cloud instance

## Step 1: Set Up GitHub Backup (Failover/Audit Trail)

### 1.1 Create Private Vault Backup Repository

```bash
# Create private repo on GitHub (or self-hosted)
# Name: cohezion-vault-backup
# Visibility: Private
# Initialize: Leave empty (we'll push from local)
```

### 1.2 Configure Git Remote for Vault

```bash
cd /home/mike-anderson/vaults/cohezion-vault

# Add GitHub remote
git remote add origin git@github.com:YOUR-USERNAME/cohezion-vault-backup.git

# Set push tracking
git branch -u origin/main main 2>/dev/null || git branch --set-upstream-to=origin/main main

# Initial push
git push -u origin main

# Verify
git remote -v
# Should show: origin  git@github.com:YOUR-USERNAME/cohezion-vault-backup.git (fetch)
```

### 1.3 Configure MCP Server to Auto-Sync

```bash
# Edit .env
export GIT_REMOTE_URL=git@github.com:YOUR-USERNAME/cohezion-vault-backup.git

# The git-sync daemon in docker-compose will now push changes every 5 minutes
# (Already configured in docker-compose.yml, just needs the URL)
```

## Step 2: Generate SSH Access Credentials (Local Machine)

### 2.1 Create Dedicated SSH Key for Cloud Claude

```bash
# Generate new key pair (no passphrase for automation)
ssh-keygen -t ed25519 -f ~/.ssh/id_cloud_claude -N "" -C "cloud-claude-vault-access"

# Verify
ls -la ~/.ssh/id_cloud_claude*
# Output:
# -rw------- id_cloud_claude (private key)
# -rw-r--r-- id_cloud_claude.pub (public key)
```

### 2.2 Add Public Key to Local SSH Server

```bash
# Add to authorized_keys (if not already there)
cat ~/.ssh/id_cloud_claude.pub >> ~/.ssh/authorized_keys

# Verify permissions (critical for SSH security)
chmod 700 ~/.ssh
chmod 600 ~/.ssh/authorized_keys

# Test: Should not prompt for password
ssh -i ~/.ssh/id_cloud_claude localhost "echo 'SSH key works'"
```

### 2.3 Restrict SSH Key to Tunnel Only

```bash
# Edit ~/.ssh/authorized_keys and add these restrictions to the line with id_cloud_claude.pub:

# BEFORE:
# ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIF... cloud-claude-vault-access

# AFTER:
no-pty,no-X11-forwarding,no-agent-forwarding,permitopen="127.0.0.1:8360" ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIF... cloud-claude-vault-access
```

This restricts the key to:
- Port 8360 tunneling only
- No TTY (can't get shell)
- No X11 forwarding
- No agent forwarding

## Step 3: Configure Cloud Claude Machine

### 3.1 Store Private Key Securely

```bash
# On cloud Claude machine:
mkdir -p ~/.ssh/cohezion
chmod 700 ~/.ssh/cohezion

# Securely transfer private key (NOT over network - use secure channel)
# Option A: Copy from secure location (best)
# Option B: Use secure key management service (AWS Secrets Manager, etc.)
# Option C: Generate on local, store in password manager, copy manually

chmod 600 ~/.ssh/cohezion/id_cloud_claude
```

### 3.2 Create SSH Tunnel Configuration

**File**: `~/.ssh/config`

```
Host vault-tunnel
    HostName YOUR-LOCAL-MACHINE-IP
    User mike-anderson
    IdentityFile ~/.ssh/cohezion/id_cloud_claude
    StrictHostKeyChecking accept-new
    UserKnownHostsFile ~/.ssh/known_hosts
    LocalForward 127.0.0.1:8360 127.0.0.1:8360
    ServerAliveInterval 60
    ServerAliveCountMax 10
    ExitOnForwardFailure yes
    ConnectionAttempts 5
    ConnectTimeout 10
```

### 3.3 Update Claude Code MCP Configuration

**File**: `~/.claude/mcp.json` (cloud instance)

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

## Step 4: Automated Tunnel Management (Production)

### 4.1 Create Tunnel Startup Script

**File**: `~/.local/bin/vault-tunnel-start.sh`

```bash
#!/bin/bash
set -e

TUNNEL_HOST="vault-tunnel"
LOCAL_PORT=8360
REMOTE_PORT=8360
LOG_FILE="~/.vault-tunnel.log"

# Check if tunnel already running
if pgrep -f "ssh.*$TUNNEL_HOST.*$LOCAL_PORT" > /dev/null; then
    echo "$(date): Tunnel already running (PID: $(pgrep -f "ssh.*$TUNNEL_HOST.*$LOCAL_PORT"))" >> "$LOG_FILE"
    exit 0
fi

# Start tunnel
echo "$(date): Starting vault tunnel to $TUNNEL_HOST..." >> "$LOG_FILE"
ssh -N -f "$TUNNEL_HOST" 2>&1 | tee -a "$LOG_FILE"

# Verify connection
sleep 2
if nc -z 127.0.0.1 $LOCAL_PORT 2>/dev/null; then
    echo "$(date): ✓ Tunnel established successfully" >> "$LOG_FILE"
else
    echo "$(date): ✗ Tunnel failed to establish" >> "$LOG_FILE"
    exit 1
fi
```

```bash
chmod +x ~/.local/bin/vault-tunnel-start.sh
```

### 4.2 Create Systemd Service (Optional, For Always-On)

**File**: `~/.config/systemd/user/vault-tunnel.service`

```ini
[Unit]
Description=Cohezion Vault SSH Tunnel
After=network-online.target
Wants=network-online.target

[Service]
Type=forking
ExecStart=/home/YOUR-USER/.local/bin/vault-tunnel-start.sh
ExecStop=/bin/bash -c 'pkill -f "ssh.*vault-tunnel"'
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=default.target
```

```bash
# Enable and start
systemctl --user enable vault-tunnel.service
systemctl --user start vault-tunnel.service

# Check status
systemctl --user status vault-tunnel.service
```

## Step 5: Health Monitoring & Failover

### 5.1 Tunnel Health Check Script

**File**: `~/.local/bin/vault-tunnel-health.sh`

```bash
#!/bin/bash

HEALTH_ENDPOINT="http://127.0.0.1:8360/health"
TUNNEL_CHECK_INTERVAL=30
MAX_FAILURES=3
FAILURE_COUNT=0

log_event() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" >> ~/.vault-tunnel-health.log
}

while true; do
    if curl -s -m 5 "$HEALTH_ENDPOINT" > /dev/null 2>&1; then
        FAILURE_COUNT=0
        log_event "✓ Tunnel healthy"
    else
        FAILURE_COUNT=$((FAILURE_COUNT + 1))
        log_event "✗ Health check failed ($FAILURE_COUNT/$MAX_FAILURES)"

        if [ $FAILURE_COUNT -ge $MAX_FAILURES ]; then
            log_event "Reconnecting tunnel..."
            pkill -f "ssh.*vault-tunnel" || true
            sleep 5
            ~/.local/bin/vault-tunnel-start.sh
            FAILURE_COUNT=0
        fi
    fi

    sleep $TUNNEL_CHECK_INTERVAL
done
```

```bash
chmod +x ~/.local/bin/vault-tunnel-health.sh

# Run as background service or in tmux
tmux new-session -d -s vault-health ~/.local/bin/vault-tunnel-health.sh
```

### 5.2 GitHub Backup Verification

```bash
# Check vault backup status (runs on local machine, every hour via cron)
cd /home/mike-anderson/vaults/cohezion-vault

# View recent commits
git log --oneline -5

# Check if synced to GitHub
git log --oneline -1
git remote -v show origin
```

## Step 6: Access Control & Monitoring

### 6.1 Monitor SSH Access

```bash
# On local machine - view tunnel connections
sudo journalctl -u sshd -f

# See active port forward
ss -tuln | grep 8360

# View IP of cloud instance
ps aux | grep "ssh.*vault-tunnel" | grep -v grep
```

### 6.2 Audit MCP Access

```bash
# Check nginx logs (if running via docker-compose with nginx)
docker logs cloud-vault-nginx | grep "POST\|Bearer"

# Or on local machine, view auth logs
grep "Accepted\|Failed" /var/log/auth.log | tail -20
```

### 6.3 Token Rotation Strategy

```bash
# Current token: a712027605bbd33068da5462bbcc18d90f844df23f948f124908fa726d678263

# Generate new token (every 90 days, per security best practices)
python3 -c "import hashlib,os; print(hashlib.sha256(os.urandom(32)).hexdigest())"

# Update on local machine:
# 1. Edit .env
MCP_API_KEY=<NEW_TOKEN>

# 2. Restart server
docker-compose restart mcp-server

# 3. Update cloud machine ~/.claude/mcp.json
{
  "Authorization": "Bearer <NEW_TOKEN>"
}

# 4. No restart needed for Claude Code - auto-reloads on next session
```

## Step 7: Testing & Verification

### 7.1 Test Local Connectivity

```bash
# Check server is running
curl http://localhost:8360/health

# Check Bearer token works
curl -H "Authorization: Bearer a712027605bbd33068da5462bbcc18d90f844df23f948f124908fa726d678263" \
  http://localhost:8360/mcp

# Should return MCP server info (no "Unauthorized" error)
```

### 7.2 Test From Cloud Machine

```bash
# Step 1: Start tunnel
ssh -N -f vault-tunnel

# Step 2: Verify port is open locally
nc -zv 127.0.0.1 8360

# Step 3: Test vault tool
curl -H "Authorization: Bearer a712027605bbd33068da5462bbcc18d90f844df23f948f124908fa726d678263" \
  http://127.0.0.1:8360/mcp

# Step 4: Test from Claude Code
# In Claude Code CLI, vault tools should now be available
```

### 7.3 Test Failover

```bash
# On cloud machine:
# Kill tunnel
pkill -f "ssh.*vault-tunnel"

# Verify it reconnects automatically (health check script)
sleep 60
nc -zv 127.0.0.1 8360  # Should succeed again
```

## Step 8: Disaster Recovery

### 8.1 Vault Backup Verification

```bash
# On local machine:
cd /home/mike-anderson/vaults/cohezion-vault

# Verify GitHub backup is current
git fetch origin
git log origin/main --oneline -5

# Should show recent auto-sync commits like:
# abc1234 auto-sync: 2026-02-15T22:30:00Z
# def5678 auto-sync: 2026-02-15T22:25:00Z
```

### 8.2 Restore from GitHub (If Local Vault Lost)

```bash
# On any machine with git:
git clone git@github.com:YOUR-USERNAME/cohezion-vault-backup.git /home/recovery/cohezion-vault

# Restore to original location
sudo mv /home/recovery/cohezion-vault /home/mike-anderson/vaults/cohezion-vault

# Update docker-compose volume mount and restart
```

## Step 9: Maintenance Checklist

**Daily**:
```bash
# Check tunnel health
curl http://127.0.0.1:8360/health

# Check for SSH errors
grep "ssh\|tunnel" ~/.vault-tunnel.log | tail -5
```

**Weekly**:
```bash
# Verify GitHub backup is current
cd /home/mike-anderson/vaults/cohezion-vault
git log --oneline -1 | grep "auto-sync"

# Check MCP server logs for errors
docker logs cloud-vault-mcp | grep "ERROR"
```

**Monthly**:
```bash
# Rotate Bearer token
# Generate new token and update .env + cloud mcp.json

# Review and rotate SSH keys (every 6 months)
ls -lh ~/.ssh/id_cloud_claude
```

## Reference: Network Diagram

```
┌─────────────────────┐
│   Cloud Claude      │
│  ~/.claude/mcp.json │
└──────────┬──────────┘
           │
           │ HTTP + Bearer Token
           │ (via SSH tunnel)
           │
      ssh -N -f vault-tunnel
           │
┌──────────┴──────────────────────────┐
│     SSH Tunnel (Encrypted)          │
│  127.0.0.1:8360 ←→ local:8360      │
└──────────┬──────────────────────────┘
           │
┌──────────┴──────────────────────────┐
│  Local Machine (mike-anderson)      │
│  ┌──────────────────────────────┐   │
│  │ MCP Server :8360             │   │
│  │ ├─ vault_read                │   │
│  │ ├─ vault_write               │   │
│  │ ├─ vault_search              │   │
│  │ └─ compound_* tools          │   │
│  └──────────┬───────────────────┘   │
│             │                       │
│  ┌──────────┴───────────────────┐   │
│  │ Vault Data                    │   │
│  │ /vaults/cohezion-vault/       │   │
│  │ ├─ decisions/                 │   │
│  │ ├─ patterns/                  │   │
│  │ ├─ experiments/               │   │
│  │ └─ .git/                      │   │
│  └──────────────────────────────┘   │
│                                     │
│  ┌──────────────────────────────┐   │
│  │ Git Sync Daemon              │   │
│  │ Auto-commit every 5 min      │   │
│  │ Auto-push to GitHub          │   │
│  └──────────────────────────────┘   │
└─────────────────────────────────────┘
           │
    git push origin main
           │
┌──────────┴──────────────────────┐
│    GitHub Private Repo          │
│ cohezion-vault-backup           │
│ (Backup + Audit Trail)          │
└─────────────────────────────────┘
```

## Security Summary

| Layer | Security Mechanism | Notes |
|-------|-------------------|-------|
| **Transport** | SSH Tunnel (ed25519) | Encrypted, unbreakable in practice |
| **Application** | Bearer Token (SHA256) | Rotate every 90 days |
| **Key Permissions** | `no-pty, permitopen` | SSH key locked to port 8360 only |
| **Audit** | GitHub auto-backup | Every commit tracked, visible history |
| **Monitoring** | Health checks every 30s | Auto-reconnect on failure |
| **Failover** | Git remote backup | Can restore within minutes |

## Quick Commands (Cheat Sheet)

```bash
# Cloud Machine
ssh vault-tunnel                    # Start tunnel manually
pkill -f "ssh.*vault-tunnel"       # Stop tunnel
curl http://127.0.0.1:8360/health # Check health

# Local Machine
git -C /home/mike-anderson/vaults/cohezion-vault log -1  # Check last sync
ssh -O check vault-tunnel           # Verify tunnel is open
docker-compose logs -f mcp-server   # Watch server logs
```

## Next Steps

1. ✅ Create GitHub backup repo
2. ✅ Generate SSH key pair
3. ✅ Add public key to local authorized_keys with restrictions
4. ✅ Store private key securely on cloud machine
5. ✅ Configure SSH config on cloud machine
6. ✅ Update ~/.claude/mcp.json on cloud machine
7. ✅ Set up health check script
8. ✅ Test tunnel connectivity
9. ✅ Verify MCP tools work from cloud
10. ✅ Set up monitoring/alerts

**Questions?** Check `MCP_CLAUDE_CODE_INTEGRATION.md` for MCP-specific help or `TROUBLESHOOTING.md` for common issues.
