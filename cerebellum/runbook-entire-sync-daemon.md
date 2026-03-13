---
title: "Runbook: Entire.io Sync Daemon"
date: 2026-02-13
status: active
tags: [runbook, operations, entire-io, daemon]
aspect: thinker
neural:
  activation: 0.8
  stage: mature
  synapse_in: 10
  synapse_out: 10
---

# Runbook: Entire.io Sync Daemon

Operational procedures for the entire.io sync daemon that polls git commits and syncs agent checkpoint data to vault notes and SurrealDB.

## Architecture

```
Git Repository (cohezion-vault)
  |
  v
EntireSyncDaemon (poll every 5 min)
  |
  |-- EntireOps.parse_commit_metadata()
  |     Extracts: agent_id, outcomes, metrics, team_status, next_actions
  |
  |-- _create_vault_note()
  |     Writes: daily/checkpoints/YYYY-MM-DD-{hash}.md
  |
  |-- _sync_to_surrealdb() (optional)
  |     Creates: session + outcome records via AgentContextOps
  |
  |-- WorkQueue (SQLite)
  |     Tracks: processed commit hashes (.entire/queue.db)
  |
  |-- DeadLetterQueue (SQLite)
        Tracks: failed commits (.entire/dlq.db)
```

## Quick Reference

| Command | Purpose |
|---------|---------|
| `entire start` | Start daemon polling loop |
| `entire status` | Show queue state |
| `entire health` | Run health checks (exit 0=healthy, 1=unhealthy) |
| `entire health --json-output` | Health check with JSON output |
| `entire backfill` | One-time sync of all historical commits |
| `entire backfill --since 2026-01-01` | Backfill from specific date |
| `entire dlq` | List failed commits |
| `entire retry <hash>` | Retry a failed commit |
| `entire test` | Test connectivity |

## Start / Stop / Restart

### Manual (foreground)

```bash
cd /home/mike-anderson/dev/cohezion/cloud-vault-mcp

# Start with defaults (poll every 5 min)
.venv/bin/python3 -m mcp_server.entire_main start

# Start with SurrealDB integration
.venv/bin/python3 -m mcp_server.entire_main start \
  --surrealdb-url http://localhost:8000

# Start with backfill from specific date
.venv/bin/python3 -m mcp_server.entire_main start \
  --since 2026-02-01 \
  --poll-interval 60

# Stop: Ctrl+C (sends SIGINT, daemon shuts down gracefully)
```

### Systemd (production)

```bash
# Install service file (one-time)
sudo cp /home/mike-anderson/dev/cohezion/cloud-vault-mcp/systemd/entire-sync.service \
  /etc/systemd/system/
sudo systemctl daemon-reload

# Start / stop / restart
sudo systemctl start entire-sync
sudo systemctl stop entire-sync
sudo systemctl restart entire-sync

# Enable auto-start on boot
sudo systemctl enable entire-sync

# View logs
journalctl -u entire-sync -f          # Follow live
journalctl -u entire-sync --since today  # Today's logs
```

## Health Checks

### CLI Health Check

```bash
.venv/bin/python3 -m mcp_server.entire_main health

# Example output:
# Entire.io Sync Daemon Health Check
# ========================================
#   [OK  ] vault_path: /home/mike-anderson/vaults/cohezion-vault
#   [OK  ] git_path: /home/mike-anderson/vaults/cohezion-vault
#   [OK  ] work_queue: 42 processed
#   [OK  ] dlq: 0 failed commits
#   [SKIP] surrealdb: not configured
#
# Overall: HEALTHY
```

### JSON Output (for monitoring)

```bash
.venv/bin/python3 -m mcp_server.entire_main health --json-output \
  --surrealdb-url http://localhost:8000

# Returns JSON:
# {
#   "healthy": true,
#   "last_sync": "2026-02-13T10:00:00+00:00",
#   "checks": {
#     "vault_path": {"status": "pass", "detail": "..."},
#     "surrealdb": {"status": "pass", "detail": "http://localhost:8000"}
#   }
# }
```

### Health Status Codes

| Status | Meaning | Action |
|--------|---------|--------|
| pass | Check passed | None |
| fail | Check failed | Investigate immediately |
| warn | Non-critical issue | Monitor, may need attention |
| skip | Check not applicable | SurrealDB not configured |

### Exit Codes

- `0` = All checks healthy
- `1` = One or more checks failed

## DLQ Management

### List Failed Commits

```bash
.venv/bin/python3 -m mcp_server.entire_main dlq

# Output:
# Dead Letter Queue
# ================================================================================
# Commit: abc123de - Failures: 3
#   Reason: Failed to parse commit abc123de: Cannot parse date: bad-date
#   Last attempt: 2026-02-13T10:00:00+00:00
```

### Retry a Failed Commit

```bash
.venv/bin/python3 -m mcp_server.entire_main retry abc123de
```

### Inspect DLQ Database Directly

```bash
sqlite3 /home/mike-anderson/vaults/cohezion-vault/.entire/dlq.db \
  "SELECT commit_hash, failure_count, failure_reason FROM dead_letter_queue;"
```

### Clear All DLQ Entries

```bash
sqlite3 /home/mike-anderson/vaults/cohezion-vault/.entire/dlq.db \
  "DELETE FROM dead_letter_queue;"
```

## Backfill

### Process All Historical Commits

```bash
.venv/bin/python3 -m mcp_server.entire_main backfill

# Output:
# Backfill Results
# ========================================
# Total commits scanned: 150
# Entire.io commits found: 23
# Successfully processed: 23
# Skipped (already processed): 0
# Failed (sent to DLQ): 0
```

### Backfill Since Date

```bash
.venv/bin/python3 -m mcp_server.entire_main backfill --since 2026-02-01
```

### Backfill with SurrealDB

```bash
.venv/bin/python3 -m mcp_server.entire_main backfill \
  --surrealdb-url http://localhost:8000 \
  --since 2026-01-01
```

## Troubleshooting

### Daemon Not Processing Commits

1. Check health: `entire health`
2. Verify git path is correct and accessible
3. Check if commits have entire.io markers (look for "entire.io", "entire-checkpoint", "session summary", "outcomes achieved" in commit body)
4. Check DLQ for parsing failures: `entire dlq`

### SurrealDB Sync Failing

SurrealDB is optional. If it fails, vault notes are still created.

1. Check SurrealDB is running: `curl http://localhost:8000/health`
2. Check health with SurrealDB: `entire health --surrealdb-url http://localhost:8000`
3. Check daemon logs: `journalctl -u entire-sync --since "5 min ago"`
4. Look for "SurrealDB sync failed" warnings in logs

### High DLQ Count

1. List failures: `entire dlq`
2. Common causes:
   - Malformed commit dates (ParsingError)
   - Disk full (can't write vault notes)
   - Permission errors on vault directory
3. Fix root cause, then retry: `entire retry <hash>`

### Daemon Crashes / Restart Loop

1. Check systemd status: `systemctl status entire-sync`
2. Check recent logs: `journalctl -u entire-sync --since "30 min ago"`
3. Verify Python environment: `.venv/bin/python3 -c "import mcp_server.entire_main"`
4. Test manually: `entire test`

## Monitoring Checklist

| Check | Frequency | Command |
|-------|-----------|---------|
| Daemon running | Every 5 min | `systemctl is-active entire-sync` |
| Health check | Every 15 min | `entire health --json-output` |
| DLQ count | Daily | `entire dlq` |
| Processed count | Weekly | `entire status` |
| Disk usage (.entire/) | Weekly | `du -sh ~/.../cohezion-vault/.entire/` |

## File Locations

| File | Path |
|------|------|
| Source | `/home/mike-anderson/dev/cohezion/cloud-vault-mcp/src/mcp_server/entire_sync_daemon.py` |
| CLI | `/home/mike-anderson/dev/cohezion/cloud-vault-mcp/src/mcp_server/entire_main.py` |
| Parser | `/home/mike-anderson/dev/cohezion/cloud-vault-mcp/src/mcp_server/entire_ops.py` |
| Tests | `/home/mike-anderson/dev/cohezion/cloud-vault-mcp/tests/test_entire_sync_daemon.py` |
| Service | `/home/mike-anderson/dev/cohezion/cloud-vault-mcp/systemd/entire-sync.service` |
| Work queue | `/home/mike-anderson/vaults/cohezion-vault/.entire/queue.db` |
| DLQ | `/home/mike-anderson/vaults/cohezion-vault/.entire/dlq.db` |
| Checkpoint notes | `/home/mike-anderson/vaults/cohezion-vault/daily/checkpoints/` |

## Related

- [[runbook-health-checks]] - General infrastructure health checks
- [[implementation-first-infrastructure-later]] - Development pattern

## Related Concepts

- [[2026-02-13-track-b-entire-sync-daemon-complete]]
- [[2026-02-13-phase-2-track-b-entire-io-sync-daemon-complete]]
- [[phase1-production-validation-runbook]]
- [[runbook-benchmarking-validation]]
- [[entire-io-sync-daemon-design]]
- [[runbook-ci-cd-pipeline]]
- [[runbook-ollama-mcp-operations]]
- [[entire-io-sync-daemon-operations]]
