---
title: Operational Runbook - Health Checks & Monitoring
date: 2026-02-10
status: active
tags: [runbook, operations, monitoring, health-checks]
aspect: thinker
neural:
  activation: 0.96
  stage: mature
  synapse_in: 0
  synapse_out: 11
---

## Overview

Health check endpoint monitors all critical system dependencies and provides incident detection.

**Endpoint:** `GET http://localhost:8360/health`

**Response Format:**
```json
{
  "status": "healthy",
  "timestamp": "2026-02-10T14:32:45.123456Z",
  "checks": {
    "vault_accessible": {"status": "healthy", "response_time_ms": 5},
    "surrealdb_connection": {"status": "healthy", "response_time_ms": 12},
    "sheets_api_auth": {"status": "healthy", "response_time_ms": 8},
    "ollama_service": {"status": "healthy", "response_time_ms": 45},
    "ollama_mcp": {"status": "healthy", "response_time_ms": 32}
  }
}
```

## Reading Health Check Response

### Overall Status Codes

| Status | Meaning | Action Required |
|--------|---------|-----------------|
| `healthy` | All checks passed | No action needed |
| `degraded` | Some checks failing, system partially functional | Investigate failing check |
| `unhealthy` | Critical checks failing | Immediate remediation needed |

### Response Time Thresholds

**Healthy ranges (milliseconds):**
- Vault file access: < 50ms
- SurrealDB query: < 100ms
- Sheets API: < 500ms
- Ollama service: < 1000ms
- Ollama MCP: < 500ms

**If response time > thresholds:** System is slow but may be operational. Investigate root cause.

### Example: Healthy Response
```bash
curl http://localhost:8360/health | jq .

# Output: All checks return "healthy" with reasonable response times
# Action: None. System is operational.
```

### Example: Degraded Response
```bash
curl http://localhost:8360/health | jq '.checks | to_entries[] | select(.value.status != "healthy")'

# Output:
# {
#   "key": "sheets_api_auth",
#   "value": {
#     "status": "unhealthy",
#     "error": "Authentication failed: invalid_grant",
#     "response_time_ms": 0
#   }
# }
# Action: Fix Sheets API authentication (see below)
```

## Troubleshooting Each Dependency

### 0. Claude Code Telemetry Corruption

**Symptom:**
```
Claude have some internal issues/ There are 2 invalid setting files
```

**Check for bloated telemetry files:**
```bash
du -sh ~/.claude/telemetry/*.json 2>/dev/null
# Files > 1MB indicate failed telemetry accumulation
```

**Causes:**
- Failed telemetry events accumulate in JSONL files indefinitely
- Files grow to MB sizes and become corrupted
- No automatic rotation/cleanup

**Fix:**
```bash
# Remove corrupted telemetry files (safe - just failed logs)
find ~/.claude/telemetry -name "*.json" -size +1M -delete

# Or remove all telemetry
rm ~/.claude/telemetry/1p_failed_events.*.json
```

**Verify:**
```bash
# Check for invalid JSON files
find ~/.claude -name "*.json" -exec python3 -c "import json; json.load(open('{}'))" \; 2>&1 | grep -c "error"
# Should return 0
```

**Prevention:**
Add to monthly maintenance:
```bash
# Check telemetry sizes
du -sh ~/.claude/telemetry/*.json 2>/dev/null | awk '$1 ~ /M/ && $1 > 1 {print "ALERT: "$0}'
```

---

### 0.1 Debug Log Bloat

**Symptom:**
- Performance degradation
- Slow Claude Code startup
- Disk space warnings

**Check for bloated debug logs:**
```bash
# Check total size
du -sh ~/.claude/debug/

# List logs over 10MB
find ~/.claude/debug -name "*.txt" -size +10M -exec ls -lh {} \; | awk '{print $5, $9}'

# Count total logs
ls ~/.claude/debug/*.txt 2>/dev/null | wc -l
```

**Expected**: <100MB total, no logs >50MB
**Alert if**: >500MB total or any log >100MB

**Causes:**
- **Mailbox polling storms**: 734K+ calls/session from idle agents
- **MCP connection retry spam**: Failed servers retry indefinitely
- **Validation errors**: ZodError accumulation (329+ per session)
- **No log rotation**: Logs accumulate to GB sizes

**Fix:**
```bash
# Delete logs over 10MB
find ~/.claude/debug -name "*.txt" -size +10M -delete

# Delete logs older than 30 days
find ~/.claude/debug -name "*.txt" -mtime +30 -delete

# Verify cleanup
du -sh ~/.claude/debug/
```

**Prevention:**
```bash
# Add to weekly maintenance (crontab)
0 3 * * 1 find ~/.claude/debug -name "*.txt" -size +10M -delete
0 3 * * 1 find ~/.claude/debug -name "*.txt" -mtime +30 -delete
```

**Reference**: [[2026-02-10-debug-log-bloat-analysis]] - 1.6GB forensic analysis

---

### 1. Vault Inaccessible

**Symptom:**
```json
{
  "vault_accessible": {
    "status": "unhealthy",
    "error": "Vault path does not exist",
    "path": "/home/user/vaults/cohezion-vault"
  }
}
```

**Causes:**
- Vault directory deleted or moved
- Wrong path in environment variable
- File permissions issue
- Network mount disconnected

**Fixes:**

```bash
# Check if vault exists
ls -ld /home/mike-anderson/vaults/cohezion-vault
# If not found: Vault was deleted or moved

# Check environment variable
echo $VAULT_PATH
# Should be: /home/mike-anderson/vaults/cohezion-vault

# Fix wrong path
export VAULT_PATH=/home/mike-anderson/vaults/cohezion-vault
# Or update .env file or docker compose config

# Check file permissions
ls -l /home/mike-anderson/vaults/cohezion-vault
# User running service must have read access
chmod 755 /home/mike-anderson/vaults/cohezion-vault

# If network mount: Check connectivity
mount | grep cohezion-vault
umount /path/to/mount
mount -a
```

### 2. SurrealDB Connection Failed

**Symptom:**
```json
{
  "surrealdb_connection": {
    "status": "unhealthy",
    "error": "Connection refused: http://localhost:8000",
    "response_time_ms": 0
  }
}
```

**Causes:**
- SurrealDB service not running
- Wrong connection URL
- Port 8000 not listening
- Firewall blocking connection

**Fixes:**

```bash
# Check if SurrealDB is running
curl http://localhost:8000/health
# If no response: Service not running

# Start SurrealDB
surreal start --log info file:/tmp/surreal.db &

# Verify it's listening
netstat -tlnp | grep 8000
# Expected: tcp 0 0 0.0.0.0:8000 LISTEN

# Check connection URL in config
echo $SURREALDB_URL
# Should be: http://localhost:8000

# Test connection from command line
curl http://localhost:8000/health

# If using Docker
docker ps | grep surreal
# If not running:
docker run -d --name surreal -p 8000:8000 surrealdb/surrealdb
```

### 3. Sheets API Authentication Failed

**Symptom:**
```json
{
  "sheets_api_auth": {
    "status": "unhealthy",
    "error": "Authentication failed: invalid_grant",
    "response_time_ms": 150
  }
}
```

**Causes:**
- Google credentials expired
- Credentials file missing
- ADC (Application Default Credentials) not configured
- x-goog-user-project header missing

**Fixes:**

```bash
# Check if credentials file exists
ls -l ~/.config/gcloud/application_default_credentials.json

# If not found: Set up Google Cloud authentication
gcloud auth application-default login
# This creates the credentials file

# Check Google Cloud project ID
echo $GOOGLE_CLOUD_PROJECT
# Should be: cohezion-477604

# Or set manually
export GOOGLE_CLOUD_PROJECT=cohezion-477604

# Verify credentials are fresh
gcloud auth application-default print-access-token
# If error: Credentials expired, run login command above

# Check if using correct header (x-goog-user-project)
grep -r "x-goog-user-project" /home/mike-anderson/dev/cohezion/cloud-vault-mcp/
# Should include: "x-goog-user-project: cohezion-477604"
```

**Note:** Sheets API is optional. If disabled, status will show "disabled" instead of "unhealthy".

### 4. Ollama Service Down

**Symptom:**
```json
{
  "ollama_service": {
    "status": "unhealthy",
    "error": "Connection refused: http://localhost:11434",
    "response_time_ms": 0
  }
}
```

**Causes:**
- Ollama service crashed
- Not listening on port 11434
- Resource exhaustion (OOM)
- GPU driver issue

**Fixes:**

```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags
# If no response: Service not running

# Start Ollama service
ollama serve &

# Check logs for errors
journalctl -u ollama -n 50 | tail -20

# Check if listening on correct port
netstat -tlnp | grep 11434
# Expected: tcp 0 0 0.0.0.0:11434 LISTEN

# Check system resources
free -h    # Memory usage
df -h      # Disk space
nvidia-smi  # GPU memory (if NVIDIA)

# If out of memory
pkill ollama
# Remove unnecessary models
ollama rm model-name:tag
# Restart with smaller model pool
ollama serve &

# If GPU issue
nvidia-smi  # Check for errors
# Update NVIDIA driver if needed
```

### 5. Ollama MCP Server Unresponsive

**Symptom:**
```json
{
  "ollama_mcp": {
    "status": "unhealthy",
    "error": "Timeout after 5 seconds",
    "response_time_ms": 5000
  }
}
```

**Causes:**
- Ollama MCP server crashed
- Hanging request to Ollama service
- Resource contention
- Infinite loop or deadlock in MCP code

**Fixes:**

```bash
# Check if Ollama MCP server is running
ps aux | grep ollama-mcp
# If not found: Process crashed

# Check MCP server logs (if running in foreground)
# Look for exception or hang messages

# Restart Ollama MCP server
# Via Claude Code: Settings → MCP → Reload
# Or manually:
cd /home/mike-anderson/dev/cohezion/ollama-mcp
.venv/bin/python3 -m mcp_server.server

# Check Ollama service is responsive
curl http://localhost:11434/api/tags --max-time 5
# If timeout: Ollama is hung

# If Ollama is hung, restart it
pkill -f "ollama serve"
sleep 2
ollama serve &

# Monitor for hangs
# Run health check every 10 seconds
watch -n 10 'curl -s http://localhost:8360/health | jq .status'
```

## Continuous Health Monitoring

### Manual Health Checks

**Quick check (daily):**
```bash
curl -s http://localhost:8360/health | jq '.status'
# Expected: "healthy"
```

**Detailed check (weekly):**
```bash
curl -s http://localhost:8360/health | jq '.'
# Review all checks and response times
```

### Automated Health Monitoring

**Option 1: Cron job (check every 5 minutes)**
```bash
# Create health check script
cat > /tmp/monitor_health.sh << 'EOF'
#!/bin/bash
HEALTH=$(curl -s http://localhost:8360/health)
STATUS=$(echo $HEALTH | jq -r '.status')
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

if [ "$STATUS" != "healthy" ]; then
  echo "[$TIMESTAMP] ALERT: System unhealthy!"
  echo $HEALTH | jq '.'
  # Send alert (email, Slack, etc.)
else
  echo "[$TIMESTAMP] System healthy"
fi
EOF

chmod +x /tmp/monitor_health.sh

# Add to crontab (every 5 minutes)
(crontab -l; echo "*/5 * * * * /tmp/monitor_health.sh >> /tmp/health_monitor.log 2>&1") | crontab -

# Verify cron job
crontab -l | grep monitor_health
```

**Option 2: Systemd timer (more robust)**
```bash
# Create systemd service
sudo tee /etc/systemd/system/health-check.service << EOF
[Unit]
Description=Cohezion Health Check Monitor
After=network.target

[Service]
Type=oneshot
ExecStart=/tmp/monitor_health.sh
User=mike-anderson
StandardOutput=journal
StandardError=journal
EOF

# Create timer (runs every 5 minutes)
sudo tee /etc/systemd/system/health-check.timer << EOF
[Unit]
Description=Cohezion Health Check Monitor Timer
Requires=health-check.service

[Timer]
OnBootSec=1min
OnUnitActiveSec=5min
AccuracySec=10s

[Install]
WantedBy=timers.target
EOF

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable health-check.timer
sudo systemctl start health-check.timer

# Check status
sudo systemctl status health-check.timer
```

### Alerting Strategy

**If status becomes unhealthy:**

1. Log the incident: `echo "ALERT: $HEALTH" >> /var/log/cohezion-health.log`
2. Send notification: Email, Slack, PagerDuty
3. Trigger automatic remediation (optional):
   - Restart failed service
   - Page on-call engineer if critical

## Health Check Response Time Analysis

### Expected Performance Baseline

Run this to establish baseline:

```bash
# Capture baseline (run weekly or after major changes)
for i in {1..10}; do
  echo "Run $i:"
  time curl -s http://localhost:8360/health | jq '.checks | to_entries[] | "\(.key): \(.value.response_time_ms)ms"'
  sleep 1
done > /tmp/health_baseline_$(date +%Y-%m-%d).txt
```

**Compare to baseline:**
- If response time increases by > 50%: Investigate degradation
- If new timeouts appear: Check affected service

## Common Issues & Quick Fixes

| Check | Unhealthy | Quick Fix | Verify |
|-------|-----------|----------|--------|
| Vault | "Path not found" | `export VAULT_PATH=/correct/path` | `curl /health \| jq .checks.vault` |
| SurrealDB | "Connection refused" | `surreal start file:/tmp/db.db &` | `curl localhost:8000/health` |
| Sheets | "Auth failed" | `gcloud auth application-default login` | `gcloud auth application-default print-access-token` |
| Ollama | "Connection refused" | `ollama serve &` | `curl localhost:11434/api/tags` |
| Ollama MCP | "Timeout" | Restart Claude Code | `ps aux \| grep ollama` |

## Related Documentation
- [[2026-02-10-phase-a-implementation-complete]]
- [[runbook-ollama-mcp-operations]]
- [[troubleshooting-mcp-infrastructure]]
- [[mcp-infrastructure-architecture]]

## Related Concepts

- [[runbook-entire-sync-daemon]]
- [[phase1-production-validation-runbook]]
- [[runbook-benchmarking-validation]]
- [[runbook-ci-cd-pipeline]]
- [[runbook-ollama-mcp-operations]]
- [[entire-io-sync-daemon-operations]]
- [[runbook-sheets-research-pipeline]]
- [[troubleshooting-mcp-infrastructure]]
