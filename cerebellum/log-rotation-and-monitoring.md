---
title: Log Rotation and Monitoring Pattern
date: 2026-02-10
tags: [pattern, operations, logging, maintenance]
status: active
source: 2026-02-10 debug log bloat analysis
aspect: thinker
neural:
  activation: 0.82
  stage: mature
  synapse_in: 8
  synapse_out: 15
---

# Log Rotation and Monitoring Pattern

## Problem

Application logs accumulate indefinitely without rotation, causing:
- Disk space exhaustion (1.6GB+ in `~/.claude/debug/`)
- Performance degradation from large file I/O
- "Setting issues" warnings
- Difficulty troubleshooting (signal lost in noise)

## Solution

Implement automated log rotation, compression, and monitoring.

## Implementation

### 1. Manual Cleanup (Immediate)

```bash
# Clean logs older than 30 days
find ~/.claude/debug -name "*.txt" -mtime +30 -delete

# Clean logs over 10MB
find ~/.claude/debug -name "*.txt" -size +10M -delete

# Clean all except current session
find ~/.claude/debug -name "*.txt" ! -name "$(readlink ~/.claude/debug/latest | xargs basename)" -delete

# Verify cleanup
du -sh ~/.claude/debug/
```

### 2. Automated Rotation (Cron)

```bash
# Create rotation script
cat > /tmp/rotate_claude_logs.sh << 'EOF'
#!/bin/bash
LOG_DIR="$HOME/.claude/debug"
MAX_SIZE_MB=50
MAX_AGE_DAYS=30
CURRENT_SESSION=$(readlink "$LOG_DIR/latest" | xargs basename)

# Compress logs over 50MB
find "$LOG_DIR" -name "*.txt" ! -name "$CURRENT_SESSION" -size +${MAX_SIZE_MB}M -exec gzip {} \;

# Delete logs older than 30 days
find "$LOG_DIR" -name "*.txt.gz" -mtime +${MAX_AGE_DAYS} -delete
find "$LOG_DIR" -name "*.txt" -mtime +${MAX_AGE_DAYS} ! -name "$CURRENT_SESSION" -delete

# Log rotation stats
TOTAL_SIZE=$(du -sh "$LOG_DIR" | cut -f1)
echo "[$(date)] Log rotation complete. Total size: $TOTAL_SIZE"
EOF

chmod +x /tmp/rotate_claude_logs.sh

# Add to crontab (run daily at 3 AM)
(crontab -l 2>/dev/null; echo "0 3 * * * /tmp/rotate_claude_logs.sh >> /tmp/log_rotation.log 2>&1") | crontab -
```

### 3. Health Monitoring (Weekly)

```bash
# Check log directory health
cat > /tmp/check_log_health.sh << 'EOF'
#!/bin/bash
LOG_DIR="$HOME/.claude/debug"
WARN_SIZE_MB=200
ALERT_SIZE_MB=500

TOTAL_MB=$(du -sm "$LOG_DIR" | cut -f1)

if [ "$TOTAL_MB" -gt "$ALERT_SIZE_MB" ]; then
  echo "🚨 ALERT: Debug logs at ${TOTAL_MB}MB (threshold: ${ALERT_SIZE_MB}MB)"
  echo "Large files:"
  find "$LOG_DIR" -name "*.txt" -size +10M -exec ls -lh {} \; | awk '{print $5, $9}'
elif [ "$TOTAL_MB" -gt "$WARN_SIZE_MB" ]; then
  echo "⚠️  WARNING: Debug logs at ${TOTAL_MB}MB (threshold: ${WARN_SIZE_MB}MB)"
else
  echo "✓ Debug logs healthy: ${TOTAL_MB}MB"
fi
EOF

chmod +x /tmp/check_log_health.sh

# Add to weekly health check
echo "0 9 * * 1 /tmp/check_log_health.sh | mail -s 'Claude Code Log Health' user@example.com" | crontab -
```

### 4. Systemd Timer (Production)

```bash
# Create systemd service
sudo tee /etc/systemd/system/claude-log-rotate.service << EOF
[Unit]
Description=Claude Code Log Rotation
After=network.target

[Service]
Type=oneshot
ExecStart=/tmp/rotate_claude_logs.sh
User=$(whoami)
StandardOutput=journal
StandardError=journal
EOF

# Create timer (daily at 3 AM)
sudo tee /etc/systemd/system/claude-log-rotate.timer << EOF
[Unit]
Description=Claude Code Log Rotation Timer
Requires=claude-log-rotate.service

[Timer]
OnCalendar=daily
OnCalendar=03:00
Persistent=true

[Install]
WantedBy=timers.target
EOF

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable claude-log-rotate.timer
sudo systemctl start claude-log-rotate.timer

# Check status
sudo systemctl status claude-log-rotate.timer
```

## When to Use

- Any application without built-in log rotation
- Debug logs that accumulate over time
- Multi-session applications (Claude Code, tmux, screen)
- Long-running services with verbose logging

## Benefits

- **Disk space savings**: 90%+ with compression
- **Performance**: Smaller logs = faster I/O
- **Troubleshooting**: Recent logs easier to find
- **Compliance**: Automatic cleanup of old logs

## Trade-offs

- **Compression CPU cost**: Minimal (runs at 3 AM)
- **Lost history**: Logs deleted after 30 days
- **Cron dependency**: Requires cron or systemd

## Monitoring Metrics

```bash
# Current log directory size
du -sh ~/.claude/debug/

# Number of logs
ls ~/.claude/debug/*.txt | wc -l

# Largest 10 logs
ls -lhS ~/.claude/debug/*.txt | head -10

# Logs over 10MB
find ~/.claude/debug -size +10M -exec ls -lh {} \;

# Compression ratio
BEFORE=$(du -sm ~/.claude/debug/ | cut -f1)
gzip -k ~/.claude/debug/*.txt
AFTER=$(du -sm ~/.claude/debug/ | cut -f1)
echo "Compression saved $((BEFORE - AFTER))MB"
```

## Related Lessons
- [[2026-02-10-debug-log-bloat-analysis]] - 1.6GB accumulation forensics
- [[2026-02-10-telemetry-corruption-fix]] - Similar cleanup issue

## Related Patterns
- [[runbook-health-checks]] - Add log size check
- [[troubleshooting-mcp-infrastructure]] - MCP debugging

---

**Key Insight**: Log rotation is not a feature, it's a necessity. Without it, every application eventually fills disk and degrades performance.

## Related Decisions

- [[2026-02-22-daily-cli-tool-update-via-systemd-timer|Decision: Daily CLI Tool Update via Systemd Timer]] - Systemd timer pattern for scheduled maintenance
- [[2026-02-10-claude-log-mining-architecture|Decision: Claude Log Mining Architecture]] - Log data as a source of insight

## Related Concepts

- [[dna-origami-2d-semiconductor-patterning]]
- [[entire-io-to-vault-mapping]]
- [[automated-concept-extraction]]
- [[sheetsbr idge-mcp-testing]]
- [[runbook-entire-sync-daemon]]
- [[phase1-production-validation-runbook]]
- [[typescript-error-diagnostic]]
- [[runbook-benchmarking-validation]]
- [[daily-cli-tool-update-with-version-comparison]] — complementary systemd timer pattern for automated CLI tool version checking
