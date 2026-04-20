---
title: "Sheets Research Pipeline Operational Runbook"
date: 2026-02-10
status: complete
tags: [operations, runbook, sheets-research, daemon]
aspect: thinker
neural:
  activation: 1.0
  stage: mature
  synapse_in: 5
  synapse_out: 11
---

# Sheets Research Pipeline Operational Runbook

Production operations guide for the autonomous Google Sheets research daemon.

## Quick Reference

| Command | Purpose |
|---------|---------|
| `sudo systemctl start sheets-research-daemon` | Start the daemon |
| `sudo systemctl stop sheets-research-daemon` | Stop the daemon |
| `sudo systemctl status sheets-research-daemon` | Check daemon status |
| `journalctl -u sheets-research-daemon -f` | View live logs |
| `sheets-research-daemon dlq` | List dead letter queue |
| `sheets-research-daemon retry --row 123` | Retry a specific failed row |
| `sheets-research-daemon status` | Get daemon metrics |

---

## 1. Deployment

### Prerequisites

- Linux system (systemd)
- Python 3.12+ with venv
- Cloud Vault MCP running on port 8360
- Google Sheets API access (ADC token)
- Claude Code with OAuth configured (or ANTHROPIC_API_KEY)

### Installation Steps

#### 1. Create data directory

```bash
sudo mkdir -p /var/lib/sheets-research
sudo chown mike-anderson:mike-anderson /var/lib/sheets-research
sudo chmod 755 /var/lib/sheets-research
```

#### 2. Copy configuration file

```bash
cp /home/mike-anderson/dev/cohezion/.env.sheets-research.example \
   /home/mike-anderson/dev/cohezion/.env.sheets-research
```

Edit `.env.sheets-research` and customize:
- `VAULT_PATH` (if different)
- `SHEETS_RESEARCH_ENABLED=true` (enable daemon)
- `SHEETS_RESEARCH_POLL_INTERVAL` (adjust polling frequency)
- `SHEETS_RESEARCH_DB` (data directory location)

#### 3. Install systemd service

```bash
sudo cp /home/mike-anderson/dev/cohezion/sheets-research-daemon.service \
        /etc/systemd/system/

sudo systemctl daemon-reload
sudo systemctl enable sheets-research-daemon
sudo systemctl start sheets-research-daemon
```

#### 4. Verify startup

```bash
sudo systemctl status sheets-research-daemon
journalctl -u sheets-research-daemon -n 20
```

Expected output: `"Sheets research daemon initialized"` → `"Starting sheets research daemon"`

---

## 2. Monitoring

### Health Checks

#### Daily Health Check

```bash
# Check daemon health endpoint
curl http://localhost:8360/health | jq '.sheets_research_pipeline'
```

Expected response:
```json
{
  "status": "ok",
  "daemon_status": "running",
  "work_queue": {
    "PENDING": 0,
    "IN_PROGRESS": 0,
    "COMPLETED": 250
  },
  "dlq_size": 2,
  "rows_processed_today": 47
}
```

Alert conditions:
- `status != "ok"`: Review logs
- `dlq_size > 50`: Investigate failed rows
- `rows_processed_today == 0` (after 1 hour): Check for hangs

#### Daemon Status

```bash
# Get detailed daemon metrics
sheets-research-daemon status
```

Shows work queue stats, DLQ size, and daily row count.

#### Log Inspection

```bash
# View last 50 lines
journalctl -u sheets-research-daemon -n 50

# Follow logs in real-time
journalctl -u sheets-research-daemon -f

# Filter for errors
journalctl -u sheets-research-daemon -p err

# Last hour of logs
journalctl -u sheets-research-daemon --since "1 hour ago"
```

### Key Metrics to Track

| Metric | Healthy | Warning | Critical |
|--------|---------|---------|----------|
| DLQ size | <10 | 10-50 | >50 |
| Daemon uptime | >99% | 95-99% | <95% |
| Rows/day | >100 | 50-100 | <50 |
| Memory usage | <500MB | 500-1G | >1G |
| Batch success rate | >90% | 80-90% | <80% |

---

## 3. Troubleshooting

### Daemon Won't Start

**Symptom**: `systemctl start` fails

**Diagnosis**:
```bash
sudo systemctl status sheets-research-daemon
journalctl -u sheets-research-daemon -n 30
```

**Common causes**:

1. **Cloud Vault MCP not running**
   ```bash
   # Check if MCP is up
   curl http://localhost:8360/health

   # Start MCP if down
   sudo systemctl start cloud-vault-mcp
   ```

2. **Permission error on SQLite database**
   ```bash
   ls -la /var/lib/sheets-research/
   # Fix permissions
   sudo chown mike-anderson:mike-anderson /var/lib/sheets-research
   ```

3. **Missing .env file**
   ```bash
   ls -la /home/mike-anderson/dev/cohezion/.env.sheets-research
   # Create if missing
   cp .env.sheets-research.example .env.sheets-research
   ```

4. **Python venv issue**
   ```bash
   # Verify venv
   /home/mike-anderson/dev/cohezion/.venv/bin/python3 --version
   ```

### Daemon Hangs (No Rows Processed)

**Symptom**: Daemon running but no rows researched for >2 hours

**Diagnosis**:
```bash
# Check logs for errors
journalctl -u sheets-research-daemon --since "2 hours ago" | grep -i "error\|timeout\|failed"

# Get daemon status
sheets-research-daemon status

# Check work queue state
sqlite3 /var/lib/sheets-research/work_queue.db "SELECT COUNT(*) FROM work_queue WHERE state='IN_PROGRESS';"
```

**Common causes**:

1. **Agent spawn failures (no claude CLI)**
   ```bash
   # Verify claude CLI available
   which claude
   claude ask "test" --model claude-haiku-4-5-20251001 --max-turns 1
   ```

2. **Google Sheets API timeout**
   ```bash
   # Test Sheets Bridge manually
   python3 -c "from mcp_server.sheets_bridge import SheetsBridge; b = SheetsBridge(); rows = b.get_all_rows(); print(f'Got {len(rows)} rows')"
   ```

3. **Batch processing stuck**
   ```bash
   # Check work queue state
   sqlite3 /var/lib/sheets-research/work_queue.db \
     "SELECT COUNT(*) as stuck FROM work_queue WHERE state='IN_PROGRESS' AND last_attempt < datetime('now', '-30 minutes');"
   ```

   If stuck > 0, rows are stalled in IN_PROGRESS. Restart daemon:
   ```bash
   sudo systemctl restart sheets-research-daemon
   ```

### High Failure Rate (DLQ Growing)

**Symptom**: Many rows in dead letter queue

**Diagnosis**:
```bash
# Show DLQ entries
sheets-research-daemon dlq

# Count by failure reason
sqlite3 /var/lib/sheets-research/work_queue_dlq.db \
  "SELECT failure_reason, COUNT(*) FROM dead_letter_queue GROUP BY failure_reason;"
```

**Common causes**:

1. **Link timeouts (web unavailable)**
   - Check if external services are down
   - Increase `SHEETS_RESEARCH_AGENT_TIMEOUT` in `.env.sheets-research`

2. **JSON parsing failures**
   - Agent may not be returning valid JSON
   - Check recent agent outputs in logs
   - Adjust max_turns in daemon configuration if needed

3. **Google Sheets API errors**
   - Check Sheets API quota
   - Verify quota project in `.env.sheets-research`
   - Check gcloud ADC token: `gcloud auth application-default print-access-token`

### Memory Leak

**Symptom**: Memory usage grows unbounded

**Diagnosis**:
```bash
# Check daemon process memory
ps aux | grep sheets_research_main
top -p <pid>  # Monitor memory over time
```

**Solution**:
```bash
# Restart daemon (systemd auto-restart handles this)
sudo systemctl restart sheets-research-daemon
```

---

## 4. Dead Letter Queue Management

### Viewing DLQ

```bash
sheets-research-daemon dlq
```

Shows all failed rows with reason and failure count.

### Investigating Failed Rows

```bash
# Get specific row details
sqlite3 /var/lib/sheets-research/work_queue_dlq.db \
  "SELECT * FROM dead_letter_queue WHERE row_number = 123;"
```

### Retrying Individual Rows

```bash
# Retry a specific row (moves back to work queue)
sheets-research-daemon retry --row 123

# Verify it was moved
sheets-research-daemon dlq
```

Row will be processed in next daemon cycle.

### Marking Rows as Permanently Inaccessible

```bash
# Remove from DLQ without retrying (link is broken/paywalled)
sheets-research-daemon mark-inaccessible --row 123
```

Use for:
- Dead links (404, 410)
- Paywalled articles
- Geo-blocked content
- Sites requiring authentication

### Bulk DLQ Operations

```bash
# Export DLQ to CSV for analysis
sqlite3 /var/lib/sheets-research/work_queue_dlq.db \
  ".mode csv" \
  ".headers on" \
  "SELECT * FROM dead_letter_queue;" > dlq_export.csv

# Clear entire DLQ (careful!)
sqlite3 /var/lib/sheets-research/work_queue_dlq.db \
  "DELETE FROM dead_letter_queue;"
```

---

## 5. Performance Tuning

### Adjust Polling Frequency

Edit `.env.sheets-research`:
```bash
# Process more frequently (higher CPU cost)
SHEETS_RESEARCH_POLL_INTERVAL=180  # 3 minutes instead of 5

# Process less frequently (lower cost)
SHEETS_RESEARCH_POLL_INTERVAL=600  # 10 minutes instead of 5
```

Restart daemon:
```bash
sudo systemctl restart sheets-research-daemon
```

### Increase Batch Size

```bash
# Process more rows per cycle (higher API cost)
SHEETS_RESEARCH_BATCH_SIZE=20  # 20 rows per agent (default: 10)
```

Trade-off: More rows/cycle but higher token cost and potential timeout risk.

### Increase Concurrent Agents

```bash
# Spawn more agents in parallel
SHEETS_RESEARCH_MAX_CONCURRENT_AGENTS=8  # 8 agents (default: 4)
```

Trade-off: Faster processing but higher token quota usage and API rate limiting risk.

### Adjust Agent Timeout

```bash
# Longer timeout for slow links
SHEETS_RESEARCH_AGENT_TIMEOUT=600  # 10 minutes (default: 5)
```

---

## 6. Maintenance

### Weekly Tasks

1. **Review DLQ size**
   ```bash
   sheets-research-daemon status | grep dlq_size
   ```
   If >10 rows, investigate patterns.

2. **Check disk usage**
   ```bash
   du -sh /var/lib/sheets-research/
   ```
   Expected: <100MB

3. **Verify backups**
   ```bash
   ls -la /var/lib/sheets-research/*.db*
   ```

### Monthly Tasks

1. **Archive old data**
   ```bash
   # Backup completed rows
   sqlite3 /var/lib/sheets-research/work_queue.db \
     ".dump work_queue" | gzip > backup_wq_$(date +%Y%m%d).sql.gz
   ```

2. **Analyze failure patterns**
   ```bash
   sqlite3 /var/lib/sheets-research/work_queue_dlq.db \
     "SELECT failure_reason, COUNT(*) as count FROM dead_letter_queue GROUP BY failure_reason ORDER BY count DESC;"
   ```

### Quarterly Tasks

1. **Optimize database**
   ```bash
   sqlite3 /var/lib/sheets-research/work_queue.db "VACUUM;"
   sqlite3 /var/lib/sheets-research/work_queue_dlq.db "VACUUM;"
   ```

2. **Review performance metrics**
   - Average rows/day
   - Success rate
   - DLQ patterns
   - Cost tracking

---

## 7. Alerts & Escalation

### Alert Thresholds

| Alert | Threshold | Action |
|-------|-----------|--------|
| Daemon down | >5 min | Check logs, restart if needed |
| DLQ overflow | >50 rows | Investigate failure patterns |
| Memory growth | >1.5G | Restart daemon |
| Rows stuck | >5 in IN_PROGRESS for >1h | Restart daemon |
| Success rate | <80% | Review recent agent outputs |

### Investigation Checklist

When issues occur:

- [ ] Check daemon status: `sudo systemctl status sheets-research-daemon`
- [ ] Review recent logs: `journalctl -u sheets-research-daemon --since "1 hour ago"`
- [ ] Check work queue: `sheets-research-daemon status`
- [ ] Inspect DLQ: `sheets-research-daemon dlq`
- [ ] Verify Cloud Vault MCP: `curl http://localhost:8360/health`
- [ ] Verify Google Sheets API: Test a manual Sheets Bridge call
- [ ] Check disk space: `df -h`
- [ ] Check memory: `free -h`

---

## 8. Rollback & Shutdown

### Emergency Shutdown

```bash
# Stop daemon immediately
sudo systemctl stop sheets-research-daemon

# Disable auto-restart
sudo systemctl disable sheets-research-daemon
```

### Restart After Issues

```bash
# Clear any stuck state
sqlite3 /var/lib/sheets-research/work_queue.db \
  "UPDATE work_queue SET state='PENDING' WHERE state='IN_PROGRESS';"

# Re-enable and start
sudo systemctl enable sheets-research-daemon
sudo systemctl start sheets-research-daemon
```

### Remove Daemon

```bash
sudo systemctl stop sheets-research-daemon
sudo systemctl disable sheets-research-daemon
sudo rm /etc/systemd/system/sheets-research-daemon.service
sudo systemctl daemon-reload
```

---

## 9. Logging Reference

### Log Levels

- **INFO**: Normal operations (rows processed, batches completed)
- **WARNING**: Non-critical issues (DLQ additions, high memory)
- **ERROR**: Failures requiring investigation (agent crashes, API errors)

### Important Log Patterns

```bash
# Successful poll cycle
"Sheets research daemon starting"
"Found X unresearched rows"
"Spawning N agents"
"Processed X rows successfully"

# Retry logic
"Row N moved to DLQ after 3 attempts"
"Retrying row N from DLQ"

# Errors
"Agent failed with code"
"JSON extraction failed"
"Batch update failed"
"Batch update failed"
```

---

## 10. Contact & Support

**Documentation**:
- Implementation plan: `decisions/2026-02-10-event-driven-sheets-research.md`
- Architecture: `concepts/sheets-research-pipeline-architecture.md`
- Daily notes: `daily/2026-02-10-sheets-research-*.md`

**Team**:
- Implementation lead: Claude (Haiku 4.5)
- Deployment contact: mike-anderson

**Related Runbooks**:
- Cloud Vault MCP: `patterns/runbook-ci-cd-pipeline.md`
- Health checks: `patterns/runbook-health-checks.md`

---

**Last Updated**: 2026-02-10
**Status**: Production Ready
**Next Review**: 2026-02-17

## Related

- [[token-efficiency]]
- [[compound-engineering]]
- [[agentic-ai]]

## Related Concepts

- [[2026-02-13-track-b-entire-sync-daemon-complete]]
- [[2026-02-13-phase-2-track-b-entire-io-sync-daemon-complete]]
- [[runbook-entire-sync-daemon]]
- [[phase1-production-validation-runbook]]
- [[runbook-benchmarking-validation]]
- [[entire-io-sync-daemon-design]]
- [[runbook-ci-cd-pipeline]]
- [[runbook-ollama-mcp-operations]]
