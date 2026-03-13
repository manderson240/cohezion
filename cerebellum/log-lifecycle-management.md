---
title: 'Log Lifecycle Management Pattern'
date: 2026-02-19
tags: [pattern]
aspect: thinker
neural:
  activation: 0.8
  stage: growing
  synapse_in: 6
  synapse_out: 6
---
# Log Lifecycle Management Pattern

**Tags:** #pattern #operations #logging #incident-response #storage-governance
**Date:** 2026-02-19
**Context:** Feb 2026 SurrealDB crash-loop incident (129K restarts, 1.2GB journal growth)

## Overview

A three-layer approach to log lifecycle management that prevents both unbounded growth AND panic-mode destructive cleanup. The core principle: **diagnostics must be captured before data is purged**.

## Problem Statement

During the Feb 10-18, 2026 SurrealDB crash-loop incident, multiple systems failed:
1. **Crash loop** (129,121 restarts over 8 days, ~15K/day)
2. **Log explosion** (syslog: 813MB, journal: 1.2GB)
3. **Journald crash** (couldn't handle write volume)
4. **Panic vacuum** (`journalctl --vacuum-time=1s` deleted ALL historical logs)
5. **Data loss** (no crash timeline for forensic analysis)

The root cause chain:
```
No retention policy (systemd) 
  → Unbounded growth (crash loop)
    → Journald crash (out of memory)
      → Manual panic vacuum (desperation)
        → Data loss (diagnostics destroyed)
```

## Solution Architecture

### Layer 1: Extraction Before Purge

Extract crash timelines into structured archives BEFORE rotation/vacuum operations:

**Tools:**
- `scripts/maintenance/extract_crash_timeline.sh` — Parameterized extraction script
  - Accepts: `--service`, `--from`, `--to` (date range)
  - Outputs: Markdown timeline + compressed archive (zstd)
  - Handles: RFC 3339 timestamps, gzipped rotated logs, deduplication

**Workflow:**
```bash
# Extract before rotation
./extract_crash_timeline.sh --service "cohezion-surreal" --from "2026-02-10" --to "2026-02-18"

# Creates:
# - data/archives/2026-02-crash-loop/timeline.md (8.8KB structured report)
# - data/archives/2026-02-crash-loop/raw-crash-events.log.zst (3MB compressed, 1.4GB uncompressed)
```

**Key insight:** 6.9M events → 3MB compressed archive (0.04% of original size). Extraction is cheap; panic deletion is catastrophic.

### Layer 2: System-Level Retention Policies

Configure retention budgets at the system level so logs self-manage:

**Journald** (`systemd/journald-cohezion.conf`):
```ini
[Journal]
SystemMaxUse=2G           # Hard cap on disk usage
SystemKeepFree=4G         # Safety valve
SystemMaxFileSize=128M    # Easier rotation
MaxRetentionSec=30day     # Keep history
RateLimitBurst=1000       # Limit crash-loop flood
```

**Logrotate** (`systemd/logrotate-rsyslog.conf`):
```
/var/log/syslog {
    rotate 8              # Keep 8 rotations (compressed: ~7-18MB each)
    weekly                # Normal schedule
    maxsize 100M          # Early rotation on crash loops
    compress
    delaycompress
}
```

**Install scripts:**
- `scripts/maintenance/install_journald_config.sh --check` → Verify without sudo
- `scripts/maintenance/install_logrotate_config.sh --check` → Verify config

### Layer 3: Storage Lifecycle Monitoring

Lightweight bash script that alerts BEFORE budgets are exceeded:

**Script:** `scripts/maintenance/storage_lifecycle.sh`
**Integration:** Called by `scripts/service_guardian.sh` every 2 minutes

**Storage Budgets:**

| Area | Budget | Alert At | Purpose |
|------|--------|----------|---------|
| System journal | 2GB | 1.5GB (75%) | Prevent journald crash |
| Syslog rotations | 500MB | 400MB | Detect crash loops early |
| Crash reports | 100MB | 80MB | Monitor systemd coredumps |
| SurrealDB data | 500MB | 400MB | Detect data bloat |
| Cohezion vault | 1GB | 800MB | Knowledge base health |
| Log archives | 1GB | 800MB | Prevent archive accumulation |
| Total /var/log | 3GB | 2.5GB | Overall log budget |

**Alert mechanisms:**
- Write to `data/guardian_events.jsonl` (event type: `storage_warning`)
- Desktop notification via `notify-send`
- Early warning: Flag individual syslog files > 200MB (crash loop indicator)

**Output modes:**
- Human-readable: ASCII table with color-coded warnings
- JSON: Machine-readable for dashboards (`--json`)

## Destructive Operations Pre-Flight Checklist

**NEVER run destructive log commands without completing this checklist:**

1. **Inventory:** What data exists?
   - `journalctl --disk-usage` (journal size)
   - `ls -lh /var/log/syslog*` (syslog sizes)
   - `du -sh /var/crash` (crash reports)

2. **Recoverability:** What data is recoverable from alternatives?
   - Journald → rsyslog (systemd messages also in syslog)
   - Rsyslog → journal (application logs also in journal)
   - Crash reports → journal/syslog (crash metadata in logs)

3. **Non-recoverable data:** What is ONLY in the target?
   - Journal binary data (structured fields, metadata)
   - Memory-only state (current systemd counters)

4. **Extract before destroying:**
   - Run `extract_crash_timeline.sh` for incident forensics
   - Copy unique data sources (not duplicated elsewhere)
   - Verify archive is readable: `zstd -d <archive> -c | head`

5. **Verify backup:**
   - Check file exists and size > 0
   - Test decompression without errors
   - Verify key events present in archive

6. **THEN proceed with destructive operation:**
   - `journalctl --vacuum-time=7d` (NOT 1s!)
   - `sudo logrotate -f /etc/logrotate.d/rsyslog`

## Enforcement Mechanisms

**Git hook** (`.claude/hooks/guard-services.sh`):
```bash
# Block destructive log commands without pre-flight
if grep -qE "journalctl.*--vacuum-|rm -rf /var/log" "$commit_msg"; then
    echo "ERROR: Destructive log operation detected"
    echo "Run extraction first: scripts/maintenance/extract_crash_timeline.sh"
    exit 1
fi
```

**Storage lifecycle monitor:** Alerts BEFORE manual intervention is needed

**Automated retention:** System-level policies prevent unbounded growth

## Incident Timeline (Feb 10-18, 2026)

**Extracted with `extract_crash_timeline.sh`:**

| Date | Events | Restart Counter | Key Events |
|------|--------|-----------------|------------|
| Feb 10 | 777K | Started at ~1K | Crash loop begins (MANIFEST corruption) |
| Feb 11 | 817K | ~15K | Daily failure rate stabilizes |
| Feb 12 | 812K | ~30K | Syslog grows to 200MB+ |
| Feb 13 | 797K | ~45K | Journal exceeds 1GB |
| Feb 14 | 810K | ~61K | Journald crash (first occurrence) |
| Feb 15 | 798K | ~76K | Desktop portal crash (cascade failure) |
| Feb 16 | 793K | ~91K | Syslog exceeds 800MB |
| Feb 17 | 780K | ~107K | Manual intervention (services stopped) |
| Feb 18 | 528K | ~122K | MANIFEST repaired, StartLimitBurst added, restart |

**Total:** 6,912,904 events, 129,121 service restarts

**Cascade chain:**
1. SurrealDB MANIFEST corruption (root cause)
2. Infinite restart loop (no StartLimitBurst)
3. Log explosion (no size limits)
4. Journald crash (OOM from write flood)
5. Desktop portal crash (journald dependency)
6. System instability (multiple service failures)

**Resolution:**
- Stopped cohezion-surreal.service (break crash loop)
- Repaired MANIFEST file (root cause fix)
- Added StartLimitBurst=10 to [Unit] section (prevent future loops)
- Created this log lifecycle management system

## Lessons Learned

1. **Prevention > Cleanup:** Retention policies prevent crises; panic vacuums cause data loss
2. **Early warning > Emergency response:** 200MB syslog alerts BEFORE 800MB crisis
3. **Diagnostics before deletion:** Extract timelines before rotating logs
4. **Bash > Python for resilience:** Guardian scripts must survive codebase breakage
5. **Alert, don't auto-delete:** Automated deletion is how we lost the journal in the first place
6. **Compress aggressively:** 1.4GB → 3MB with zstd -19 (460:1 ratio for repetitive logs)
7. **System-level budgets:** logrotate + journald enforce limits without manual intervention
8. **Hooks prevent accidents:** Guard against destructive commands in commits

## Related Decisions

- [[2026-02-19-block-destructive-system-operations-from-ai-tools|Block Destructive System Operations from AI Tools]] — the architectural decision that resulted in adding pre-flight enforcement hooks for operations like `journalctl --vacuum`
- [[2026-02-09-operational-principle-no-destructive-operations-without-learning|Operational Principle: No Destructive Operations Without Learning]] — the general principle this pattern operationalizes for log management specifically
- [[compound-engineering-investigation-retrospection-before-destructive-operations|Compound Engineering: Investigation Before Destructive Operations]] — the conceptual foundation

## Related Patterns

- **Systemd Crash-Loop Prevention:** Use StartLimitBurst/Interval in [Unit] section
- **Service Guardian:** Lightweight crash detection (no Python dependencies)
- **Artifact Governance:** Three-tier storage (Git, SurrealDB, External) for large data

## Implementation Checklist

- [ ] Extract crash timeline (if incident active)
- [ ] Install journald config: `sudo scripts/maintenance/install_journald_config.sh`
- [ ] Install logrotate config: `sudo scripts/maintenance/install_logrotate_config.sh`
- [ ] Verify storage monitor: `scripts/maintenance/storage_lifecycle.sh --json`
- [ ] Add `data/archives/` to `.gitignore`
- [ ] Verify guardian integration: Check `scripts/service_guardian.sh` calls storage_lifecycle.sh

## References

- Incident timeline: `data/archives/2026-02-crash-loop/timeline.md`
- Raw events archive: `data/archives/2026-02-crash-loop/raw-crash-events.log.zst`
- Journald config: `systemd/journald-cohezion.conf`
- Logrotate config: `systemd/logrotate-rsyslog.conf`
- Guard hook: `.claude/hooks/guard-services.sh`

## Decisions That Produced This Pattern

- [[2026-02-09-operational-principle-no-destructive-operations-without-learning]] — the operational governance principle whose "Extract Learning" step this pattern implements
- [[2026-02-10-claude-log-mining-architecture]] — the log mining architecture whose pipeline feeds into this lifecycle management pattern
- [[2026-02-10-log-mining-adversarial-review]] — adversarial review that validated the log mining approach
- [[2026-02-10-operational-forensics-compound-engineering]] — the forensics approach that applies this log lifecycle to extract compound engineering learnings
