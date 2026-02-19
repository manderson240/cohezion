# Log Lifecycle Management Implementation Plan

Created: 2026-02-19
Status: VERIFIED
Approved: Yes
Iterations: 0
Worktree: Yes

> **Status Lifecycle:** PENDING -> COMPLETE -> VERIFIED
> **Iterations:** Tracks implement->verify cycles (incremented by verify phase)
>
> - PENDING: Initial state, awaiting implementation
> - COMPLETE: All tasks implemented
> - VERIFIED: All checks passed
>
> **Approval Gate:** Implementation CANNOT proceed until `Approved: Yes`
> **Worktree:** Yes - uses git worktree isolation

## Summary

**Goal:** Extract the crash-loop timeline from bloated syslog files (1.4GB logical, ~220MB on-disk with ZFS) before they rotate away, then implement a storage lifecycle strategy that prevents both unbounded growth and panic-mode destructive cleanup. The principle: **diagnostics must be captured before data is purged**.

**Architecture:** Three-layer approach: (1) Extract and archive crash timeline from syslogs into a compact structured report + compressed archive, (2) Configure system-level retention policies (logrotate, journald) so logs self-manage within budgets, (3) Create a lightweight storage lifecycle script that the existing guardian timer can invoke to monitor and alert on storage anomalies before they become crises.

**Tech Stack:** bash (extraction, storage monitor, logrotate config), systemd (journald config, timer integration), gzip/zstd (archive compression)

## Scope

### In Scope
- Extract crash timeline (Feb 10-18) from syslog/syslog.1 into structured report
- Compress and archive the raw crash-period syslog data before logrotate purges it
- Install journald drop-in config (already created at `systemd/journald-cohezion.conf`)
- Configure rsyslog/logrotate with size-aware rotation to prevent 800MB syslog files
- Create a storage lifecycle monitor that integrates with the existing guardian timer
- Log learnings to vault about the full incident lifecycle (cause -> crisis -> panic -> data loss -> recovery)

### Out of Scope
- Changing rsyslog daemon config (forwarding, filtering) - just logrotate policies
- Implementing external storage tiers (S3, gdrive) - document for future
- SurrealDB data lifecycle (already managed by guardian_reporter.py)
- Application-level log management (Python logging config)
- Changes to the existing `weekly_repo_maintenance.sh` (git-focused, different concern)

## Prerequisites
- sudo access for: journald drop-in install, logrotate config changes
- Existing guardian timer running (`cohezion-guardian.service`)

## Context for Implementer

- **Current disk state:** 2TB NVMe, 311GB used, 1.26TB available, ZFS (1.03x compression)
- **Log sizes (logical):** syslog=585MB (Feb 15-19), syslog.1=813MB (Feb 8-15), journal=213MB (Feb 17-19)
- **Log sizes (ZFS-compressed on disk):** syslog=93MB, syslog.1=128MB, journal=214MB, /var/log total=478MB
- **Crash timeline:** SurrealDB crash loop started Feb 10, ~15K failures/day, totaling ~106K failures across Feb 10-18. Fixed Feb 18 (services stopped, MANIFEST repaired, StartLimitBurst added).
- **Logrotate config:** `/etc/logrotate.d/rsyslog` - weekly rotation, keep 4 rotations, compress after 1 rotation. This means syslog.1 (uncompressed, 813MB) will become syslog.2.gz (~18MB) on Feb 22 (next Saturday rotation).
- **Urgency:** syslog.1 (containing Feb 8-15 crash data) will be rotated to syslog.2.gz on ~Feb 22, pushing syslog.4.gz off the retention cliff. The crash data survives rotation (just compressed), but extraction should happen before the next rotation for simplicity.
- **Guardian integration:** `scripts/service_guardian.sh` runs every 2 minutes via `cohezion-guardian.service` timer. Storage checks can piggyback on this.
- **Guard hook:** `.claude/hooks/guard-services.sh` already blocks `journalctl --vacuum-*` and `rm -rf /var/log` (added earlier this session).
- **Journald config:** `systemd/journald-cohezion.conf` already created (SystemMaxUse=2G, MaxRetentionSec=30day, RateLimitBurst=1000). Needs sudo to install.
- **Patterns to follow:** Guardian script style in `scripts/service_guardian.sh` (pure bash, no Python deps, JSONL event logging)
- **Gotchas:** ZFS compression means `du -sh` shows compressed sizes but `ls -la` shows logical sizes. Use `du` for actual disk impact, `ls` for understanding data volume.

## Progress Tracking

**MANDATORY: Update this checklist as tasks complete. Change `[ ]` to `[x]`.**

- [x] Task 1: Extract crash timeline and archive raw data
- [x] Task 2: Install journald retention config
- [x] Task 3: Harden logrotate for syslog size limits
- [x] Task 4: Create storage lifecycle monitor
- [x] Task 5: Log incident learnings to vault

**Total Tasks:** 5 | **Completed:** 5 | **Remaining:** 0

## Implementation Tasks

### Task 1: Extract Crash Timeline and Archive Raw Data

**Objective:** Extract the Feb 10-18 SurrealDB crash-loop timeline from syslog files into a structured Markdown report (for human reading and vault storage) and a compressed archive (for future forensic reference). Then the bloated syslogs can be safely reduced knowing nothing is lost.

**Dependencies:** None

**Files:**
- Create: `scripts/maintenance/extract_crash_timeline.sh` (extraction script, reusable for future incidents)
- Create: `data/archives/2026-02-crash-loop/timeline.md` (structured crash report)
- Create: `data/archives/2026-02-crash-loop/raw-crash-events.log.zst` (compressed unique crash events)

**Key Decisions / Notes:**
- Extract ONLY unique/interesting events, not the 106K repetitive "Failed with result" lines. The report should contain:
  - First and last occurrence of each failure type per day (with timestamps)
  - Daily failure counts (already known: ~15K/day from Feb 10-18)
  - Cascade events: journald crash, desktop portal crash, reboot events
  - cohezion-lab.service GROUP errors (separate root cause)
  - Any OOM, kernel panic, or other system-level events
- Archive format: extract all cohezion/surreal/crash-related lines from syslog + syslog.1, deduplicate, compress with zstd (best ratio for log data)
- The extraction script should be parameterizable for future incidents: `./extract_crash_timeline.sh --service "cohezion-surreal" --from "2026-02-10" --to "2026-02-18"`
- Script must handle already-rotated .gz files (search syslog, syslog.1, syslog.*.gz) using zcat/zgrep for compressed files
- Deduplication must preserve frequency data: keep first+last occurrence per day with timestamps AND daily counts. The raw archive keeps everything; the timeline.md summarizes
- Add `data/archives/` to `.gitignore` (compressed logs should not be in git)
- After extraction is verified, the raw syslogs will be reduced by logrotate naturally (Task 3 configures tighter rotation). No manual deletion of syslogs.

**Definition of Done:**
- [ ] `data/archives/2026-02-crash-loop/timeline.md` exists with structured per-day crash counts and cascade events
- [ ] `data/archives/2026-02-crash-loop/raw-crash-events.log.zst` exists with compressed unique events
- [ ] `scripts/maintenance/extract_crash_timeline.sh` is executable and works with `--service`, `--from`, `--to` flags
- [ ] `data/archives/` is in `.gitignore`

**Verify:**
- `test -f data/archives/2026-02-crash-loop/timeline.md && echo "Timeline exists"`
- `zstd -l data/archives/2026-02-crash-loop/raw-crash-events.log.zst` shows file info
- `bash scripts/maintenance/extract_crash_timeline.sh --help` shows usage

### Task 2: Install Journald Retention Config

**Objective:** Install the already-created `systemd/journald-cohezion.conf` as a drop-in config for systemd-journald, so journal size is capped at 2GB with 30-day retention. This prevents both unbounded growth and the need for future panic vacuums.

**Dependencies:** None

**Files:**
- Existing: `systemd/journald-cohezion.conf` (already created, ready to install)
- Create: `scripts/maintenance/install_journald_config.sh` (idempotent install script with verification)

**Key Decisions / Notes:**
- Script must: (1) check if drop-in already installed, (2) copy to `/etc/systemd/journald.conf.d/cohezion.conf`, (3) restart systemd-journald, (4) verify new settings took effect
- Requires sudo - script should check for sudo access and fail gracefully with instructions
- Idempotent: running twice should be safe (compare checksums before overwriting)
- Verify settings with `systemd-analyze cat-config systemd/journald.conf`

**Definition of Done:**
- [ ] `scripts/maintenance/install_journald_config.sh` exists and is executable
- [ ] Script is idempotent (safe to run multiple times)
- [ ] Script verifies installation after applying
- [ ] Running script with sudo installs config and restarts journald

**Verify:**
- `bash scripts/maintenance/install_journald_config.sh --check` reports current state
- After sudo install: `systemd-analyze cat-config systemd/journald.conf 2>/dev/null | grep -c SystemMaxUse` returns 1

### Task 3: Harden Logrotate for Syslog Size Limits

**Objective:** Add size-based rotation to rsyslog's logrotate config so syslog files can't grow to 800MB+ between weekly rotations. If a crash loop fills syslog, rotation triggers early.

**Dependencies:** Task 1 (crash timeline must be extracted BEFORE forced rotation purges data)

**Files:**
- Create: `systemd/logrotate-rsyslog.conf` (our desired config, stored in repo)
- Create: `scripts/maintenance/install_logrotate_config.sh` (install script)

**Key Decisions / Notes:**
- Add `maxsize 100M` to rsyslog logrotate config. This triggers rotation when ANY individual log file exceeds 100MB, regardless of the weekly schedule. Combined with `rotate 8` (up from 4), this keeps ~800MB max compressed history.
- Keep weekly rotation as the baseline (for normal operation)
- Increase `rotate` from 4 to 8 to retain more history (compressed rotations are small — syslog.2.gz is only 7MB)
- The config file lives in the repo at `systemd/logrotate-rsyslog.conf` for version control; the install script copies it to `/etc/logrotate.d/rsyslog`
- Requires sudo for install
- After install, force an immediate rotation of the current bloated syslog: `sudo logrotate -f /etc/logrotate.d/rsyslog`

**Definition of Done:**
- [ ] `systemd/logrotate-rsyslog.conf` contains size-limited rotation config
- [ ] `scripts/maintenance/install_logrotate_config.sh` exists and is executable
- [ ] Config adds `maxsize 100M` and `rotate 8` to rsyslog rotation

**Verify:**
- `grep maxsize systemd/logrotate-rsyslog.conf` shows `maxsize 100M`
- `bash scripts/maintenance/install_logrotate_config.sh --check` reports current state

### Task 4: Create Storage Lifecycle Monitor

**Objective:** Create a lightweight storage monitor script that checks disk usage across all managed areas (logs, journals, data directories, crash reports, vault) and alerts when thresholds are exceeded. Integrates with the existing guardian timer so it runs every 2 minutes.

**Dependencies:** Task 1, Task 2, Task 3 (budgets must align with configured retention policies)

**Files:**
- Create: `scripts/maintenance/storage_lifecycle.sh` (pure bash, no Python deps)
- Modify: `scripts/service_guardian.sh` (add timeout-wrapped call to storage_lifecycle.sh)

**Key Decisions / Notes:**
- Pure bash (same philosophy as service_guardian.sh) — must survive any Python/cohezion breakage
- Storage budget table (these are ALERT thresholds, not hard limits):

  | Area | Path | Budget | Alert At |
  |------|------|--------|----------|
  | System journal | `/var/log/journal/` | 2GB | 1.5GB (75%) |
  | Syslog (all rotations) | `/var/log/syslog*` | 500MB | 400MB |
  | Crash reports | `/var/crash/` | 100MB | 80MB |
  | SurrealDB data | `data/surrealdb/` | 500MB | 400MB |
  | Cohezion vault | `~/vaults/cohezion-vault/` | 1GB | 800MB |
  | Archives | `data/archives/` | 1GB | 800MB |
  | Total /var/log | `/var/log/` | 3GB | 2.5GB |

- Alert action: write to guardian_events.jsonl (existing pattern) with event type `storage_warning`
- Desktop notification via `notify-send` when any threshold exceeded
- Output a one-line summary suitable for the guardian's periodic output
- Guardian integration must use timeout wrapper: `timeout 10s bash storage_lifecycle.sh || echo "storage check timeout"` to prevent hangs from blocking service health checks
- All budgets are COMPRESSED (on-disk) sizes measured via `du -sb`, not logical sizes (ZFS may compress)
- mkdir -p any monitored directory that might not exist yet; warn but don't crash on missing paths
- The script should also check for syslog files > 200MB (early warning of a new crash loop filling logs)
- **Key principle: alert, don't delete.** Automated deletion of logs is what caused the original problem. The monitor warns; the human decides.

**Definition of Done:**
- [ ] `scripts/maintenance/storage_lifecycle.sh` exists, is executable, checks all areas in budget table
- [ ] Script writes `storage_warning` events to `data/guardian_events.jsonl` when thresholds exceeded
- [ ] `scripts/service_guardian.sh` calls storage_lifecycle.sh
- [ ] Script runs successfully and reports storage state

**Verify:**
- `bash scripts/maintenance/storage_lifecycle.sh` outputs storage summary without errors
- `bash scripts/maintenance/storage_lifecycle.sh --json` outputs machine-readable state

### Task 5: Log Incident Learnings to Vault

**Objective:** Create a comprehensive vault note documenting the full incident lifecycle (cause -> crisis -> panic vacuum -> data loss -> recovery) with actionable learnings. This is the "capture learnings before purging data" step — ensuring the knowledge survives even after the raw logs are eventually rotated away.

**Dependencies:** Task 1 (timeline extraction informs the learnings)

**Files:**
- Create: vault note via `vault_write` MCP tool (not a file in the repo)

**Key Decisions / Notes:**
- Log as a vault pattern (reusable) rather than just a decision (one-time)
- Include the full cascade chain with timestamps
- Include the storage budget table from Task 4 as a reference
- Include the "destructive operations checklist" pattern:
  1. What data exists? (inventory)
  2. What data is recoverable? (check alternatives — syslog, crash reports, etc.)
  3. What data is NOT recoverable? (journal binary data, memory-only state)
  4. Export/backup before destroying
  5. Verify backup is readable
  6. THEN proceed with destructive operation
- Reference the guard-services.sh hook as the enforcement mechanism

**Definition of Done:**
- [ ] Vault note created with full incident timeline
- [ ] Vault note includes "Destructive Operations Pre-Flight Checklist" pattern
- [ ] Vault note includes storage budget table

**Verify:**
- `vault_search` for "crash loop lifecycle" returns the new note

## Testing Strategy

- **Unit tests:** Not applicable (bash scripts, system configs)
- **Integration tests:** Each install script has a `--check` mode that verifies current state without making changes
- **Manual verification:** Run each script, verify output, check system state after installation

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| logrotate `maxsize` triggers too aggressively during normal operation | Low | Low | 100MB threshold is generous; normal syslog grows ~7MB/week compressed. Only crash loops trigger early rotation |
| Forced logrotate rotation causes brief log gap | Low | Low | rsyslog picks up new file immediately via postrotate HUP signal |
| journald restart drops in-flight log entries | Low | Medium | rsyslog independently captures the same data; no single point of failure |
| Storage monitor false positives annoy user | Medium | Low | Thresholds set at 75-80% of budget, not 100%. Only alerts, never auto-deletes |
| zstd not installed for archive compression | Low | Low | Fall back to gzip if zstd unavailable; check in script |

## Open Questions

- None — scope is well-defined from exploration.

### Deferred Ideas

- External storage tier (S3/gdrive) for archives older than 90 days
- Automated syslog filtering to separate cohezion events into their own log file via rsyslog config
- Dashboard widget showing storage budget utilization
- ZFS snapshot-based backup before destructive operations
