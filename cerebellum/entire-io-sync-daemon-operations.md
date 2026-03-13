---
title: "Entire.io Sync Daemon - Operations Runbook"
date: 2026-02-13
status: guide
tags: [daemon, entire-io, operations, runbook, phase-2]
aspect: thinker
neural:
  activation: 1.0
  stage: mature
  synapse_in: 7
  synapse_out: 11
---

# Entire.io Sync Daemon - Operations Guide

This runbook covers deployment, operation, and troubleshooting of the Entire.io Sync Daemon that syncs Git commits to the vault and SurrealDB.

---

## Quick Start

### Start Daemon (Manual)
```bash
python3 -m mcp_server.entire_main start \
  --poll-interval=300 \
  --vault-path=/home/mike-anderson/vaults/cohezion-vault \
  --git-path=/home/mike-anderson/vaults/cohezion-vault
```

### Start Daemon (Systemd)
```bash
# Copy service file
sudo cp /home/mike-anderson/dev/cohezion/cloud-vault-mcp/entire-io-sync.service /etc/systemd/system/

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable entire-io-sync
sudo systemctl start entire-io-sync
```

### Check Status
```bash
# Manual daemon
python3 -m mcp_server.entire_main status

# Systemd daemon
systemctl status entire-io-sync
journalctl -u entire-io-sync -f
```

---

## Architecture

### Core Components

**1. WorkQueue (SQLite-backed)**
- Tracks processed commits by hash
- Prevents duplicate processing
- Schema: `processed_commits(commit_hash PRIMARY KEY, processed_at, status)`

**2. DeadLetterQueue (SQLite-backed)**
- Captures failed syncs with reason
- Tracks failure count per commit
- Schema: `failed_commits(commit_hash, reason, count, last_attempt)`

**3. EntireSyncDaemon (Async event loop)**
- Polls git repository for new commits
- Parses commit metadata (author, timestamp, message)
- Creates/updates vault notes
- Syncs to SurrealDB via MCP tools
- Auto-retries failed commits

**4. EntireOps (Parser module)**
- Extracts agent IDs from commit authors
- Parses session outcomes, metrics, team status
- Normalizes timestamps and formats

### Data Flow

```
Git Repository
      ↓
Poll (every 300s)
      ↓
Parse Commit Metadata
      ↓
Check WorkQueue (already processed?)
      ├─ Yes → Skip
      └─ No → Continue
            ↓
      Parse Commit Message
            ↓
      Extract Outcomes, Metrics, Team Status
            ↓
      Create Vault Note (daily/{date}/{agent}.md)
            ↓
      Record to SurrealDB (agent_logs node)
            ↓
      Mark in WorkQueue (processed)
            ↓
      Success! Next commit...
            ↓
      (On failure) → Add to DeadLetterQueue
```

---

## CLI Commands

### `start` - Run daemon

```bash
python3 -m mcp_server.entire_main start [OPTIONS]

Options:
  --poll-interval INTEGER    Polling interval in seconds (default: 300)
  --vault-path TEXT         Path to vault (default: ~/vaults/cohezion-vault)
  --git-path TEXT           Path to git repository (default: vault-path)
```

**Example**:
```bash
python3 -m mcp_server.entire_main start --poll-interval=60 --vault-path=/custom/vault
```

---

### `status` - Show daemon state

```bash
python3 -m mcp_server.entire_main status [OPTIONS]

Options:
  --vault-path TEXT         Path to vault (default: ~/vaults/cohezion-vault)
  --git-path TEXT           Path to git repository
```

**Output**:
```
Entire.io Sync Daemon Status
========================================
Status: running
Last sync: 2026-02-13T15:30:45Z
Processed commits: 145
Failed commits (DLQ): 2
Poll interval: 300s
```

---

### `dlq` - List dead letter queue

```bash
python3 -m mcp_server.entire_main dlq [OPTIONS]

Options:
  --vault-path TEXT         Path to vault
```

**Output**:
```
Dead Letter Queue
================================================================================
Commit: abc12345 - Failures: 2
  Reason: vault_path not found
  Last attempt: 2026-02-13T14:22:10Z

Commit: def67890 - Failures: 1
  Reason: invalid_commit_message
  Last attempt: 2026-02-13T14:25:33Z
```

---

### `retry` - Retry failed commit

```bash
python3 -m mcp_server.entire_main retry COMMIT_HASH [OPTIONS]

Options:
  --vault-path TEXT         Path to vault
```

**Example**:
```bash
python3 -m mcp_server.entire_main retry abc12345
```

---

### `test` - Validate daemon setup

```bash
python3 -m mcp_server.entire_main test [OPTIONS]

Options:
  --vault-path TEXT         Path to vault
  --git-path TEXT           Path to git repository
```

**Output**:
```
Testing Entire.io Sync Daemon
========================================
✓ Vault path exists
✓ Git path exists
✓ Status retrieval successful
  Processed: 145
  Failed (DLQ): 2
✓ Dead letter queue readable (2 entries)

All tests passed! Daemon is ready to run.
```

---

## Systemd Service Management

### Installation

```bash
# Copy service file to systemd directory
sudo cp entire-io-sync.service /etc/systemd/system/

# Reload systemd daemon
sudo systemctl daemon-reload

# Enable service (start on boot)
sudo systemctl enable entire-io-sync

# Start service
sudo systemctl start entire-io-sync
```

### Operations

```bash
# Check status
sudo systemctl status entire-io-sync

# View logs
sudo journalctl -u entire-io-sync -f          # Follow logs
sudo journalctl -u entire-io-sync -n 100      # Last 100 lines

# Restart daemon
sudo systemctl restart entire-io-sync

# Stop daemon
sudo systemctl stop entire-io-sync

# Disable auto-start
sudo systemctl disable entire-io-sync
```

### Service Configuration

The service file (`entire-io-sync.service`) includes:

**Auto-restart**:
- `Restart=always` - Restarts on failure
- `RestartSec=10` - Waits 10s before restart
- `StartLimitBurst=10` - Max 10 restarts in interval
- `StartLimitInterval=300` - Per 5-minute interval

**Resource Limits**:
- `MemoryLimit=256M` - Max 256MB RAM
- `CPUQuota=50%` - Max 50% CPU usage

**Security**:
- `NoNewPrivileges=true` - Prevents privilege escalation
- `ProtectSystem=strict` - Read-only filesystem except vault
- `ProtectHome=yes` - Restricted home directory access
- `ReadWritePaths` - Only vault and /tmp are writable

---

## Monitoring & Health Checks

### Health Check Endpoint

The daemon provides a status endpoint for monitoring:

```python
# Check daemon health
status = await daemon.get_status()

# Status includes:
{
    'status': 'running',                    # Current state
    'last_sync': '2026-02-13T15:30:45Z',   # Last sync timestamp
    'processed_count': 145,                 # Commits synced
    'dlq_count': 2,                         # Failed commits
    'poll_interval': 300,                   # Seconds
}
```

### Monitoring with systemd

```bash
# Watch journal in real-time
journalctl -u entire-io-sync -f

# Check restart count
systemctl show entire-io-sync --property=NRestarts

# Monitor resource usage
ps aux | grep entire_main

# Check if service is active
systemctl is-active entire-io-sync
```

### Common Alerts

**Alert: High DLQ count**
```bash
# List failed commits
python3 -m mcp_server.entire_main dlq

# Investigate reasons
journalctl -u entire-io-sync | grep "ERROR"

# Retry failed commits
python3 -m mcp_server.entire_main retry <hash>
```

**Alert: Service not running**
```bash
# Check status
sudo systemctl status entire-io-sync

# Check logs for errors
journalctl -u entire-io-sync -n 50

# Restart service
sudo systemctl restart entire-io-sync
```

**Alert: High CPU usage**
```bash
# Check CPU quota
grep CPUQuota /etc/systemd/system/entire-io-sync.service

# Check if commits are being processed
python3 -m mcp_server.entire_main status

# Increase poll interval if needed (default 300s = 5 min)
# Edit service file and restart
```

---

## Troubleshooting

### Daemon Won't Start

**Problem**: Service fails to start
```bash
sudo systemctl start entire-io-sync
# Job for entire-io-sync.service failed
```

**Solution**:
```bash
# Check error logs
journalctl -u entire-io-sync -n 30

# Common issues:
# 1. Python environment not found - verify .venv path
# 2. Vault path not found - check VAULT_PATH environment variable
# 3. Permissions denied - ensure user has read/write access

# Verify daemon manually
python3 -m mcp_server.entire_main test

# Check git repository
git -C /home/mike-anderson/vaults/cohezion-vault log --oneline -1
```

---

### Processing Takes Too Long

**Problem**: Commits not being synced quickly
```bash
python3 -m mcp_server.entire_main status
# Poll interval: 300s (syncs every 5 minutes)
```

**Solution**:
```bash
# Reduce poll interval (minimum 10s for safety)
python3 -m mcp_server.entire_main start --poll-interval=60

# Or update systemd service:
# Edit /etc/systemd/system/entire-io-sync.service
# Change: ExecStart=... --poll-interval=60
# Then: sudo systemctl daemon-reload && sudo systemctl restart entire-io-sync
```

---

### Commits Stuck in Dead Letter Queue

**Problem**: Commits failing repeatedly
```bash
python3 -m mcp_server.entire_main dlq
# Shows failures but not being processed
```

**Solution**:
```bash
# 1. Check the reason
python3 -m mcp_server.entire_main dlq
# Look at "Reason" field for failure cause

# 2. Fix root cause (e.g., missing vault directory)
mkdir -p /path/to/vault/daily

# 3. Retry specific commit
python3 -m mcp_server.entire_main retry <commit_hash>

# 4. Monitor next sync
journalctl -u entire-io-sync -f
```

---

### High Memory Usage

**Problem**: Daemon consuming excessive memory
```bash
# Check memory
ps aux | grep entire_main
# Shows daemon using >256M

# Check systemd limits
systemctl show entire-io-sync --property=MemoryLimit
```

**Solution**:
```bash
# Option 1: Restart daemon (frees memory)
sudo systemctl restart entire-io-sync

# Option 2: Increase memory limit
# Edit /etc/systemd/system/entire-io-sync.service
# Change: MemoryLimit=256M → MemoryLimit=512M
# Then: sudo systemctl daemon-reload && sudo systemctl restart entire-io-sync

# Option 3: Check for memory leaks
# Monitor memory over time
watch -n 5 'systemctl show entire-io-sync --property=MemoryCurrent'
```

---

## Performance Tuning

### Poll Interval Tuning

Default: 300s (5 minutes)

**Faster sync** (more CPU):
```bash
python3 -m mcp_server.entire_main start --poll-interval=60   # 1 minute
```

**Slower sync** (less CPU):
```bash
python3 -m mcp_server.entire_main start --poll-interval=600  # 10 minutes
```

**Recommendation**: Start with 300s, adjust based on commit frequency:
- High frequency (>10 commits/day) → 120-180s
- Medium frequency (1-10 commits/day) → 300-600s
- Low frequency (<1 commit/day) → 900-1800s

---

### Resource Limits

Systemd service limits (current):

```ini
[Service]
MemoryLimit=256M    # Max 256MB RAM
CPUQuota=50%        # Max 50% CPU
```

To adjust:
```bash
# Edit service file
sudo nano /etc/systemd/system/entire-io-sync.service

# Update limits (example):
# MemoryLimit=512M
# CPUQuota=75%

# Reload and restart
sudo systemctl daemon-reload
sudo systemctl restart entire-io-sync
```

---

## Database Maintenance

### Check Database Size

```bash
# List SQLite databases (stored in vault)
ls -lh /home/mike-anderson/vaults/cohezion-vault/.*entire* 2>/dev/null

# Or find by recent modification
find /home/mike-anderson/vaults/cohezion-vault -name "*.db" -mtime -7
```

### Backup Databases

```bash
# Backup work queue and DLQ
cp /home/mike-anderson/vaults/cohezion-vault/.entire_work_queue.db backup.db
cp /home/mike-anderson/vaults/cohezion-vault/.entire_dlq.db backup.db

# Or backup entire vault
tar czf vault_backup_$(date +%Y%m%d).tar.gz /home/mike-anderson/vaults/cohezion-vault/
```

### Clean Up Dead Letter Queue

```bash
# View DLQ
python3 -m mcp_server.entire_main dlq

# After issues are fixed and retried:
# DLQ is automatically cleaned as commits succeed

# Or restart daemon to reset (loses DLQ history)
sudo systemctl restart entire-io-sync
```

---

## Integration with SurrealDB

The daemon syncs commit data to SurrealDB via MCP tools:

```
Commit parsed
    ↓
Vault note created (daily/{date}/{agent}.md)
    ↓
SurrealDB sync: CREATE agent_logs node
    ├─ commit_hash
    ├─ agent_id
    ├─ timestamp
    ├─ outcomes
    ├─ metrics
    └─ team_status
```

### Verify SurrealDB Sync

```bash
# Query SurrealDB
curl http://localhost:8000/sql -X POST \
  -H "Accept: application/json" \
  -d "SELECT * FROM agent_logs ORDER BY timestamp DESC LIMIT 5"

# Should show recent commits with parsed data
```

---

## Integration with MCP Tools

The daemon registers as an MCP tool provider for Track B completion:

```
entire-io-sync daemon
├─ record_agent_log()      # Create agent_logs node
├─ get_sync_status()       # Query sync state
├─ retry_failed_commit()   # Retry from DLQ
└─ list_failed_commits()   # View DLQ entries
```

### Access via MCP

```python
from mcp_server.entire_sync_daemon import EntireSyncDaemon

daemon = EntireSyncDaemon(vault_path="/path/to/vault")

# Get status
status = await daemon.get_status()
print(f"Synced: {status['processed_count']}")

# Retry failed
success = await daemon.retry_failed("abc123")

# List DLQ
failed = daemon.dlq.get_all()
```

---

## Testing

### Unit Tests

```bash
cd /home/mike-anderson/dev/cohezion/cloud-vault-mcp

# Run all daemon tests
python3 -m pytest tests/test_entire_ops.py tests/test_entire_sync_daemon.py -v

# Run specific test
python3 -m pytest tests/test_entire_sync_daemon.py::TestEntireSyncDaemon::test_daemon_initialization -v

# With coverage
python3 -m pytest tests/test_entire_*.py --cov=src.mcp_server.entire --cov-report=html
```

### Integration Tests

```bash
# Test with real vault
python3 -m mcp_server.entire_main test --vault-path=/home/mike-anderson/vaults/cohezion-vault

# Test daemon connectivity
python3 -m mcp_server.entire_main status

# Verify notes are created
ls -la /home/mike-anderson/vaults/cohezion-vault/daily/
```

---

## Deployment Checklist

- [ ] Install systemd service file
- [ ] Enable auto-start: `sudo systemctl enable entire-io-sync`
- [ ] Start service: `sudo systemctl start entire-io-sync`
- [ ] Verify running: `sudo systemctl status entire-io-sync`
- [ ] Check logs: `journalctl -u entire-io-sync -n 20`
- [ ] Test status: `python3 -m mcp_server.entire_main status`
- [ ] Verify vault notes being created
- [ ] Confirm SurrealDB sync working
- [ ] Set up monitoring (optional)
- [ ] Document any customizations

---

## Appendix: Configuration Reference

### Environment Variables

```bash
# Set in /etc/systemd/system/entire-io-sync.service
VAULT_PATH=/home/mike-anderson/vaults/cohezion-vault     # Vault location
GIT_PATH=/home/mike-anderson/vaults/cohezion-vault       # Git repository
PYTHONUNBUFFERED=1                                        # Unbuffered output
```

### Default Paths

- Vault: `~/vaults/cohezion-vault`
- Daily notes: `<vault>/daily/{date}/`
- Checkpoints: `<vault>/checkpoints/`
- Work queue DB: `<vault>/.entire_work_queue.db`
- Dead letter queue DB: `<vault>/.entire_dlq.db`

### Configuration Files

- Service: `/etc/systemd/system/entire-io-sync.service`
- CLI: `/home/mike-anderson/dev/cohezion/cloud-vault-mcp/src/mcp_server/entire_main.py`
- Daemon: `/home/mike-anderson/dev/cohezion/cloud-vault-mcp/src/mcp_server/entire_sync_daemon.py`
- Ops module: `/home/mike-anderson/dev/cohezion/cloud-vault-mcp/src/mcp_server/entire_ops.py`

---

**Last Updated**: 2026-02-13
**Status**: Production Ready
**Contact**: integration-engineer (Track B lead)

See also: [[entire-io-sync-daemon-design]], [[2026-02-13-phase-2-track-b-entire-io-sync-daemon-complete]], [[2026-02-11-entire-io-api-investigation]]

## Related Concepts

- [[2026-02-13-phase-2-final-completion-summary]]
- [[2026-02-17-phase-2-full-verification-plan]]
- [[2026-02-14-track-a-sign-off-approved]]
- [[2026-02-13-phase-2-track-a-complete]]
- [[2026-02-13-track-b-entire-sync-daemon-complete]]
- [[2026-02-12-phase-2-schema-design]]
- [[2026-02-13-phase-2-execution-strategy-wave-2]]
- [[2026-02-17-phase-2-service-initialization-gap-discovery]]
