# Entire.io Sync Daemon - Deployment Guide

**Version**: 1.0
**Status**: Production-ready
**Last Updated**: 2026-02-13

---

## Quick Start (5 minutes)

```bash
# 1. Set API key
export ENTIRE_API_KEY=your_api_key_here

# 2. Start daemon
cd /path/to/cloud-vault-mcp
uv run python -m src.mcp_server.sync_cli start /path/to/repo --branch main

# 3. Check health (in another terminal)
uv run python -m src.mcp_server.sync_cli health
```

---

## Production Deployment

### Prerequisites

- Python 3.13+
- `uv` package manager installed
- Git repository initialized
- Entire.io API key (from https://entire.io/settings/api)
- Systemd (for persistent daemon)

### Installation

#### 1. Install Dependencies

```bash
cd cloud-vault-mcp
uv sync
```

#### 2. Configure Environment

Create `/etc/cohezion/entire-sync.env`:

```bash
sudo mkdir -p /etc/cohezion
sudo tee /etc/cohezion/entire-sync.env <<EOF
ENTIRE_API_KEY=your_actual_api_key_here
ENTIRE_API_URL=https://api.entire.io/v1
EOF

sudo chmod 600 /etc/cohezion/entire-sync.env
sudo chown root:root /etc/cohezion/entire-sync.env
```

#### 3. Install Systemd Service

```bash
# Copy service file
sudo cp systemd/entire-sync-daemon.service /etc/systemd/system/

# Edit service file to match your paths
sudo nano /etc/systemd/system/entire-sync-daemon.service
# Update: User, Group, WorkingDirectory, ExecStart path

# Reload systemd
sudo systemctl daemon-reload

# Enable auto-start on boot
sudo systemctl enable entire-sync-daemon

# Start daemon
sudo systemctl start entire-sync-daemon
```

#### 4. Verify Running

```bash
# Check status
sudo systemctl status entire-sync-daemon

# View logs
sudo journalctl -u entire-sync-daemon -f

# Check health
curl http://localhost:8361/health
```

---

## Configuration Options

### CLI Arguments

```bash
sync-cli start /path/to/repo \
  --branch main \              # Git branch to monitor
  --poll-interval 60 \         # Seconds between sync cycles (default: 60)
  --sync-direction bidirectional \  # bidirectional|git_to_entire|entire_to_git
  --api-url https://api.entire.io/v1 \  # API endpoint
  --api-key $ENTIRE_API_KEY    # API authentication key
```

### Sync Directions

1. **bidirectional** (default): Full 2-way sync
   - Git commits → Entire.io checkpoints
   - Entire.io checkpoints → Git commit annotations

2. **git_to_entire**: One-way Git → Entire.io
   - Only create checkpoints from new commits
   - Faster if you don't need remote checkpoint data

3. **entire_to_git**: One-way Entire.io → Git
   - Only annotate commits with checkpoint metadata
   - Useful for read-only git repositories

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ENTIRE_API_KEY` | Yes | - | API authentication key |
| `ENTIRE_API_URL` | No | https://api.entire.io/v1 | API base URL |

---

## Health Monitoring

### Health Check Endpoints

Run health server alongside daemon:

```python
# In separate terminal
uv run python -c "
from src.mcp_server.sync_health import run_health_server
from src.mcp_server.sync_daemon import get_sync_daemon
from src.mcp_server.work_queue import get_work_queue
from src.mcp_server.entire_ops import get_entire_ops

run_health_server(
    daemon_getter=lambda: get_sync_daemon(),
    queue_getter=lambda: get_work_queue(),
    entire_client_getter=lambda: get_entire_ops(),
    port=8361
)
"
```

### Available Endpoints

| Endpoint | Purpose | Success Code |
|----------|---------|--------------|
| `GET /health` | Overall health check | 200 (healthy), 503 (unhealthy) |
| `GET /metrics` | Detailed metrics | 200 |
| `GET /ready` | Readiness check | 200 (ready), 503 (not ready) |
| `GET /live` | Liveness check | 200 |

### Health Check Examples

```bash
# Overall health
curl http://localhost:8361/health
# Returns: {"status": "healthy", "uptime_seconds": 3600, "checks": {...}}

# Detailed metrics
curl http://localhost:8361/metrics
# Returns: {"daemon_stats": {...}, "queue_stats": {...}, "entire_api_health": {...}}

# Kubernetes readiness probe
curl http://localhost:8361/ready

# Kubernetes liveness probe
curl http://localhost:8361/live
```

---

## Monitoring & Alerts

### Systemd Journal Logs

```bash
# Follow logs in real-time
sudo journalctl -u entire-sync-daemon -f

# Show last 100 lines
sudo journalctl -u entire-sync-daemon -n 100

# Filter by priority (errors only)
sudo journalctl -u entire-sync-daemon -p err

# Since specific time
sudo journalctl -u entire-sync-daemon --since "1 hour ago"
```

### Log Patterns to Monitor

**Success indicators**:
```
Starting sync daemon: bidirectional (poll interval: 60s)
Syncing 3 commits to entire.io
Created checkpoint cp_123 for commit abc123
```

**Warning indicators**:
```
Queue full, dropping task
Failed to sync commit abc123: [error]
Task failed (attempt 1/3), retrying in 2s
```

**Error indicators**:
```
Sync cycle error: [error]
Task failed after 3 retries, sent to DLQ
Failed to create checkpoint: [error]
```

### Dead Letter Queue

Failed tasks are written to `~/.cohezion/sync_dlq.jsonl`:

```bash
# View DLQ entries
cat ~/.cohezion/sync_dlq.jsonl | jq '.'

# Count failed tasks
wc -l ~/.cohezion/sync_dlq.jsonl

# Review recent failures
tail -10 ~/.cohezion/sync_dlq.jsonl | jq '.'
```

---

## Performance Tuning

### Worker Pool Size

Edit `src/mcp_server/sync_daemon.py`:

```python
# Increase concurrent workers for high-throughput repos
queue = get_work_queue(max_workers=5)  # Default: 3
```

### Poll Interval

```bash
# Fast repos (many commits)
sync-cli start /repo --poll-interval 30

# Slow repos (few commits)
sync-cli start /repo --poll-interval 300
```

### Batch Size

Edit `SyncConfig` in `src/mcp_server/sync_daemon.py`:

```python
SyncConfig(
    max_batch_size=50  # Process up to 50 commits per cycle
)
```

---

## Troubleshooting

### Daemon Won't Start

**Symptom**: `systemctl start entire-sync-daemon` fails

**Solution**:
1. Check service file paths are correct
2. Verify API key is set in environment file
3. Check journalctl for error messages
4. Ensure repository path exists and is a git repo

```bash
sudo systemctl status entire-sync-daemon
sudo journalctl -u entire-sync-daemon -n 50
```

### API Connection Errors

**Symptom**: `Failed to create checkpoint: Connection refused`

**Solution**:
1. Verify API key is valid
2. Check network connectivity to entire.io
3. Test API manually: `curl -H "Authorization: Bearer $KEY" https://api.entire.io/v1/health`

```bash
# Test API key
export ENTIRE_API_KEY=your_key
curl -H "Authorization: Bearer $ENTIRE_API_KEY" https://api.entire.io/v1/health
```

### High Memory Usage

**Symptom**: Daemon using >512MB RAM

**Solution**:
1. Reduce worker pool size (default: 3)
2. Reduce max_queue_size (default: 1000)
3. Decrease poll interval (process fewer commits at once)

### Tasks Stuck in Queue

**Symptom**: Queue size keeps growing

**Solution**:
1. Check entire.io API is healthy: `curl http://localhost:8361/health`
2. Review DLQ for failing tasks: `cat ~/.cohezion/sync_dlq.jsonl`
3. Increase worker count if API is healthy
4. Fix errors causing task failures

---

## Security Considerations

### API Key Management

**Best Practices**:
- Store in `/etc/cohezion/entire-sync.env` (chmod 600)
- Use environment files, never hardcode in service file
- Rotate keys quarterly
- Use separate keys for dev/staging/prod

### Network Security

- Daemon connects to `https://api.entire.io/v1` (TLS 1.3)
- No inbound connections required
- Health endpoints listen on localhost only (127.0.0.1:8361)

### File Permissions

```bash
# Environment file (API key)
chmod 600 /etc/cohezion/entire-sync.env
chown root:root /etc/cohezion/entire-sync.env

# DLQ file
chmod 644 ~/.cohezion/sync_dlq.jsonl
chown mike-anderson:mike-anderson ~/.cohezion/sync_dlq.jsonl
```

---

## Backup & Recovery

### Backup DLQ

```bash
# Backup dead letter queue
cp ~/.cohezion/sync_dlq.jsonl ~/.cohezion/sync_dlq.$(date +%Y%m%d).jsonl

# Archive old DLQ entries (keep last 30 days)
find ~/.cohezion -name "sync_dlq.*.jsonl" -mtime +30 -delete
```

### Recovery from DLQ

```python
# Manually retry failed tasks
import json
from pathlib import Path

dlq_path = Path.home() / ".cohezion" / "sync_dlq.jsonl"
with open(dlq_path) as f:
    for line in f:
        task = json.loads(line)
        # Inspect task, fix root cause, then manually re-enqueue
        print(f"Failed: {task['id']} - {task['error_message']}")
```

---

## Upgrade Procedure

### Minor Updates (Patches)

```bash
# Stop daemon
sudo systemctl stop entire-sync-daemon

# Update code
cd /path/to/cloud-vault-mcp
git pull origin main
uv sync

# Start daemon
sudo systemctl start entire-sync-daemon

# Verify
sudo systemctl status entire-sync-daemon
```

### Major Updates (Breaking Changes)

1. Backup DLQ: `cp ~/.cohezion/sync_dlq.jsonl ~/backup/`
2. Stop daemon: `sudo systemctl stop entire-sync-daemon`
3. Update code: `git pull && uv sync`
4. Review CHANGELOG for migration steps
5. Test in dev environment first
6. Update systemd service if needed
7. Start daemon: `sudo systemctl start entire-sync-daemon`

---

## Production Checklist

Before deploying to production:

- [ ] API key configured in `/etc/cohezion/entire-sync.env`
- [ ] Systemd service installed and enabled
- [ ] Health check endpoints accessible
- [ ] Journalctl logging configured
- [ ] DLQ file location confirmed (`~/.cohezion/sync_dlq.jsonl`)
- [ ] Resource limits set (512MB RAM, 50% CPU)
- [ ] Monitoring configured (health checks every 5 minutes)
- [ ] Alert thresholds defined (DLQ size, error rate)
- [ ] Backup procedure documented
- [ ] Upgrade procedure tested in staging

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────┐
│         Systemd (Auto-restart on failure)       │
│  /etc/systemd/system/entire-sync-daemon.service │
└────────────────────┬────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────┐
│              SyncDaemon (Main Process)          │
│  ┌───────────────────────────────────────────┐  │
│  │  Event Loop (poll_interval: 60s)         │  │
│  │  ├─ git→entire: create checkpoints       │  │
│  │  └─ entire→git: annotate commits         │  │
│  └───────────────────────────────────────────┘  │
└──────────────┬──────────────┬───────────────────┘
               │              │
               ▼              ▼
┌──────────────────────┐  ┌─────────────────────┐
│   WorkQueue          │  │  Health Server      │
│   (3 workers)        │  │  (port 8361)        │
│   ├─ Priority queue  │  │  ├─ GET /health     │
│   ├─ Retry logic     │  │  ├─ GET /metrics    │
│   └─ DLQ (~/.cohezion) │  │  ├─ GET /ready     │
└──────────────────────┘  │  └─ GET /live       │
                          └─────────────────────┘
```

---

## Support

**Issues**: https://github.com/manderson240/cohezion/issues
**Documentation**: This file
**Logs**: `sudo journalctl -u entire-sync-daemon -f`
**Health Check**: `curl http://localhost:8361/health`

---

**Deployment Status**: ✅ Production-ready
**Last Tested**: 2026-02-13
**Version**: 1.0.0
