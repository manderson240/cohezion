# System Crash Root Cause Analysis and Prevention Plan

Created: 2026-02-18
Status: VERIFIED
Approved: Yes
Iterations: 0
Worktree: No

> **Status Lifecycle:** PENDING → COMPLETE → VERIFIED
> **Iterations:** Tracks implement→verify cycles (incremented by verify phase)
>
> - PENDING: Initial state, awaiting implementation
> - COMPLETE: All tasks implemented
> - VERIFIED: All checks passed
>
> **Approval Gate:** Implementation CANNOT proceed until `Approved: Yes`
> **Worktree:** No - working directly on current branch (system-level changes)

## Summary

**Goal:** Fix SurrealDB RocksDB corruption that caused a 4-day crash loop (129K+ restarts), harden all Cohezion systemd services with crash-loop prevention and resource limits, and create a lightweight service guardian as a secondary safety net that protects the system regardless of which AI tool (Claude Code, Antigravity, Gemini CLI, OpenCode) is running.

**Architecture:** Three-layer defense: (1) Fix immediate corruption and clean up, (2) Harden all systemd services with restart limits (PRIMARY crash-loop prevention via `StartLimitBurst`/`StartLimitIntervalSec` in `[Unit]` section), resource caps, and proper configuration, (3) Deploy a systemd-native watchdog timer as a SECONDARY safety net that catches cases where services lack proper limits, or where slow-burn crash loops stay under burst thresholds.

**Tech Stack:** systemd (service hardening, timers), bash (guardian script), SurrealDB 2.4.1 (RocksDB repair)

## Root Cause Analysis

### Timeline
- **Feb 14 ~13:00**: SurrealDB RocksDB MANIFEST corruption first appears. `CURRENT` file points to `MANIFEST-164765` which no longer exists on disk. SurrealDB begins crash-looping every 5 seconds.
- **Feb 14 18:35**: Briefly gets "Address already in use" errors (overlapping restarts), then back to MANIFEST errors.
- **Feb 14-18**: 129,220+ restart cycles accumulate. 57,476 LOG files created in surrealdb data directory (399MB). Each restart: fork process → init RocksDB → hit MANIFEST error → exit → repeat every 5 seconds.
- **Feb 17**: systemd-journald crashes (crash report in `/var/crash/`). Journal has grown to 1.2GB from processing 129K+ service restart log entries.
- **Feb 18 ~17:35**: Desktop crashes. `xdg-desktop-portal-gnome` core dumps (SIGABRT). Three rapid reboots follow (17:35, 17:38, 17:41). The crash loop resumes immediately after each reboot.

### Cascade Chain
```
RocksDB MANIFEST corruption
  → SurrealDB fails to start (every 5s, Restart=always, no limits)
  → 129K+ process spawns over 4 days (each initializing RocksDB - heavy I/O + memory allocation)
  → journald overwhelmed processing restart logs (1.2GB journal) → journald crash (Feb 17)
  → cohezion-lab also generating journal noise (User= bug, status 216/GROUP every 60s)
    NOTE: cohezion-lab exit 216 is lightweight (systemd rejects before forking) - contributes
    journal noise but NOT process churn. SurrealDB is the primary resource drain.
  → Combined: process churn + journal bloat → desktop portal crash → system reboot
  → Reboots can't help: same corruption persists → immediate re-crash → 3 rapid reboots
```

### Why It Wasn't Caught
1. **No restart limits**: `cohezion-surreal.service` has `Restart=always` + `RestartSec=5` with NO `StartLimitBurst`/`StartLimitIntervalSec`. systemd will restart it forever.
2. **No monitoring**: The existing `service_watchdog.py` and `health_monitor.py` scripts depend on `DaemonManager` which doesn't exist — they've never worked.
3. **No resource limits**: Services have no `MemoryMax`, `CPUQuota`, or `TasksMax` constraints.

## Scope

### In Scope
- Fix SurrealDB RocksDB MANIFEST pointer corruption
- Clean up 57K accumulated LOG files in surrealdb data directory + vacuum journal
- Harden ALL Cohezion systemd services with restart limits and resource caps
- Fix cohezion-lab.service misconfiguration (User= in user service, WantedBy=)
- Remove broken symlinks for deleted services (antiquarian, mycelium, shadow)
- Create a lightweight systemd-native service guardian (no Python dependencies)
- Update SurrealDB from deprecated `file://` to `rocksdb://` protocol (tested separately from MANIFEST fix)
- Generate a static SURREAL_PASS to replace the broken shell-substitution in .env
- Bring all services back online and verify

### Out of Scope
- Rewriting `DaemonManager` / `wake_up.py` / `service_watchdog.py` (dead code, needs separate cleanup)
- SurrealDB upgrade (staying on 2.4.1)
- Changes to the Antigravity crash (separate issue, different crash report)
- GNOME desktop portal stability (upstream bug, not our code)
- Modifying application code (this is infrastructure-only)

## Prerequisites
- sudo access for system-level service file edits (`cohezion-surreal.service` is in `/etc/systemd/system/`)
- SurrealDB binary at `/home/mike-anderson/.surrealdb/surreal` (confirmed present, v2.4.1)

## Context for Implementer

- **Service file locations:**
  - System service: `/etc/systemd/system/cohezion-surreal.service`
  - User services: `~/.config/systemd/user/cohezion-lab.service`, `ngrok-tunnel.service`, `ngrok-watchdog.service`
  - Project templates: `/home/mike-anderson/dev/cohezion/systemd/` (cohezion-lab.service, cohezion-simulation.service/timer)
  - Broken symlinks: `~/.config/systemd/user/cohezion-{antiquarian,mycelium,shadow}.service` → deleted targets
- **SurrealDB data:** `/home/mike-anderson/dev/cohezion/data/surrealdb/` (399MB, 57K files, `CURRENT` points to `MANIFEST-190877`, only `MANIFEST-190909` exists, 1 SST file, 1 WAL file)
- **Env file:** `/home/mike-anderson/dev/cohezion/.env` contains `SURREAL_DATA_PATH` and credentials.
- **CRITICAL - SURREAL_PASS:** The `.env` file has `SURREAL_PASS=$(python3 -c "import secrets; print(secrets.token_urlsafe(24))")`. systemd's `EnvironmentFile=` does NOT evaluate shell commands — it reads the literal string `$(python3 ...)` as the password. This means SurrealDB has been using a literal garbage string as its password (not regenerating). Shell clients that `source .env` get a different (evaluated) password and cannot authenticate. This must be fixed with a static password.
- **Pattern to follow:** The `ngrok-tunnel.service` already has proper restart limits (`StartLimitBurst=5`, `StartLimitInterval=600`). Use this as the template for other services.
- **CRITICAL - StartLimit placement:** `StartLimitBurst` and `StartLimitIntervalSec` MUST go in the `[Unit]` section, not `[Service]`. In `[Service]`, they may be silently ignored on systemd 255 (confirmed running). This applies to ALL service files.
- **Gotcha:** cohezion-lab.service has `User=mike-anderson` but it's a user-scoped service (runs under `systemctl --user`). User services already run as the invoking user — specifying `User=` causes "Failed to determine supplementary groups: Operation not permitted". Remove it.
- **Gotcha:** cohezion-lab.service depends on `surrealdb.service` but the actual service is `cohezion-surreal.service`. This dependency reference is wrong.
- **Gotcha:** `lab_driver.py` doesn't exist. The service references a file that was never created.
- **Gotcha:** The guardian (user service) cannot stop system services (cohezion-surreal). For system services, it logs alerts and sends desktop notifications. For user services, it can stop them directly.

## Progress Tracking

**MANDATORY: Update this checklist as tasks complete. Change `[ ]` to `[x]`.**

- [x] Task 1: Stop crash loops, fix MANIFEST, validate DB
- [x] Task 2: Clean up crash artifacts and vacuum journal
- [x] Task 3: Harden cohezion-surreal.service + fix SURREAL_PASS
- [x] Task 4: Fix and harden cohezion-lab.service
- [x] Task 5: Clean up dead service symlinks
- [x] Task 6: Harden ngrok and simulation services
- [x] Task 7: Create systemd service guardian
- [x] Task 8: Create Claude Code PreToolUse safety hooks
- [x] Task 9: Integrate with healing system and add structured logging
- [x] Task 10: Bring services online and verify

**Total Tasks:** 10 | **Completed:** 10 | **Remaining:** 0

## Implementation Tasks

### Task 1: Stop Crash Loops, Fix MANIFEST, Validate DB

**Objective:** Stop all crash-looping services immediately, fix the CURRENT file pointer, and validate that SurrealDB can actually open the repaired database before proceeding.

**Dependencies:** None

**Files:**
- Modify: `/home/mike-anderson/dev/cohezion/data/surrealdb/CURRENT` (fix pointer)

**Key Decisions / Notes:**
- **FIRST: Stop AND mask crash-looping services** to prevent accidental re-enabling during implementation:
  - `sudo systemctl stop cohezion-surreal.service && sudo systemctl mask cohezion-surreal.service`
  - `systemctl --user stop cohezion-lab.service && systemctl --user mask cohezion-lab.service`
- Backup current state: `cp -a data/surrealdb/CURRENT data/surrealdb/CURRENT.bak`
- Write correct manifest: `echo "MANIFEST-190909" > data/surrealdb/CURRENT`
- Verify MANIFEST-190909 file is valid (non-empty, 518 bytes)
- **IMMEDIATELY validate DB** by temporarily starting SurrealDB manually (not via service):
  ```bash
  /home/mike-anderson/.surrealdb/surreal start --user test --pass test file:///home/mike-anderson/dev/cohezion/data/surrealdb
  ```
  If it starts successfully → DB is recoverable. Kill it after verification.
  If it fails with a different error (missing SST, checksum mismatch) → reinitialize with fresh DB:
  ```bash
  mv data/surrealdb data/surrealdb.corrupt.bak
  mkdir -p data/surrealdb
  ```

**Definition of Done:**
- [ ] cohezion-surreal.service is stopped AND masked
- [ ] cohezion-lab.service is stopped AND masked
- [ ] CURRENT file contains `MANIFEST-190909`
- [ ] MANIFEST-190909 exists and is 518 bytes
- [ ] CURRENT.bak backup exists
- [ ] SurrealDB validated: either starts successfully with repaired DB, or fresh DB initialized

**Verify:**
- `cat /home/mike-anderson/dev/cohezion/data/surrealdb/CURRENT` shows `MANIFEST-190909`
- `systemctl is-active cohezion-surreal.service` shows `inactive`
- `systemctl is-enabled cohezion-surreal.service` shows `masked`
- Manual SurrealDB start test succeeded (or fresh DB initialized)

### Task 2: Clean Up Crash Artifacts and Vacuum Journal

**Objective:** Remove the 57K+ LOG.old files accumulated from 4 days of crash-looping, clean up stale crash reports, and vacuum the bloated systemd journal.

**Dependencies:** Task 1 (services must be stopped and masked)

**Files:**
- Clean: `/home/mike-anderson/dev/cohezion/data/surrealdb/LOG.old.*` (57K+ files)
- Clean: `/var/crash/` (old crash reports)

**Key Decisions / Notes:**
- Remove all `LOG.old.*` files: `find data/surrealdb/ -name 'LOG.old.*' -delete`
- Keep: `CURRENT`, `MANIFEST-190909`, `IDENTITY`, `LOCK`, `LOG`, `*.sst`, `*.log` (WAL), `blob/` dir
- Remove old crash reports: `sudo rm /var/crash/_usr_libexec_xdg-desktop-portal-gnome.1000.*` etc.
- **Vacuum journal** to reduce 1.2GB journal bloat and prevent residual journald instability:
  `sudo journalctl --vacuum-time=2d` (keep only last 2 days)
- Verify file count drops from 57K to <20

**Definition of Done:**
- [ ] LOG.old.* files removed from surrealdb data directory
- [ ] File count in data/surrealdb/ is under 20
- [ ] Data directory size reduced significantly
- [ ] Journal vacuumed (size reduced from 1.2GB)

**Verify:**
- `ls /home/mike-anderson/dev/cohezion/data/surrealdb/ | wc -l` shows < 20
- `du -sh /home/mike-anderson/dev/cohezion/data/surrealdb/` shows < 10MB
- `journalctl --disk-usage` shows reduced size

### Task 3: Harden cohezion-surreal.service + Fix SURREAL_PASS

**Objective:** Add crash-loop prevention, resource limits, fix the broken password, and update the SurrealDB protocol. Test protocol change separately from MANIFEST fix.

**Dependencies:** Task 1

**Files:**
- Modify: `/etc/systemd/system/cohezion-surreal.service`
- Modify: `/home/mike-anderson/dev/cohezion/.env` (fix SURREAL_PASS)

**Key Decisions / Notes:**
- **Fix SURREAL_PASS first**: Generate a static password and write it to `.env`:
  ```bash
  NEW_PASS=$(python3 -c "import secrets; print(secrets.token_urlsafe(24))")
  sed -i "s|^SURREAL_PASS=.*|SURREAL_PASS=${NEW_PASS}|" /home/mike-anderson/dev/cohezion/.env
  ```
- **Restart limits in [Unit] section** (NOT [Service] — critical for systemd 255):
  - `StartLimitBurst=5`
  - `StartLimitIntervalSec=600` (max 5 restarts per 10 minutes)
- Increase `RestartSec=5` to `RestartSec=30` (less aggressive restart)
- **Protocol change — test separately**: First verify SurrealDB starts with `file://` (known working protocol for this data). Then change to `rocksdb://` and verify again. Two separate steps.
- Add resource limits: `MemoryMax=16G` (hard safety net — prevents runaway allocations from taking down the system), `CPUQuota=200%` (limit to 2 cores), `TasksMax=256`
- **NOTE on MemoryMax vs block cache**: RocksDB auto-configures block_cache to ~50% of system RAM (66GB on 128GB system). SurrealDB 2.4.1 doesn't expose RocksDB tuning knobs directly. The `MemoryMax=16G` limit will cause SurrealDB to be OOM-killed if it tries to allocate 66GB. However, with `StartLimitBurst=5`, this converts to at most 5 OOM-kills in 10 minutes before systemd gives up — far better than infinite crash loops. If SurrealDB's RocksDB respects cgroup limits for mmap allocations, the block cache may auto-scale down. Test empirically.
- Add `ExecStartPre` health check that dynamically verifies the MANIFEST file referenced by CURRENT exists:
  `ExecStartPre=/bin/bash -c 'test -f /home/mike-anderson/dev/cohezion/data/surrealdb/$(cat /home/mike-anderson/dev/cohezion/data/surrealdb/CURRENT)'`
- Unmask service after hardening: `sudo systemctl unmask cohezion-surreal.service`
- Run `sudo systemctl daemon-reload` after changes

**Definition of Done:**
- [ ] SURREAL_PASS is a static token in .env (no shell substitution)
- [ ] StartLimitBurst=5 and StartLimitIntervalSec=600 in [Unit] section
- [ ] RestartSec changed from 5 to 30
- [ ] Protocol tested with file:// first, then changed to rocksdb://
- [ ] MemoryMax, CPUQuota, TasksMax resource limits added
- [ ] ExecStartPre validates MANIFEST existence
- [ ] Service unmasked and daemon-reload executed

**Verify:**
- `systemctl cat cohezion-surreal.service` shows all changes with StartLimit in [Unit]
- `systemctl show cohezion-surreal.service -p StartLimitBurst,StartLimitIntervalSec,MemoryMax` shows correct values
- `grep SURREAL_PASS /home/mike-anderson/dev/cohezion/.env` shows a static token (no `$(...)`)

### Task 4: Fix and Harden cohezion-lab.service

**Objective:** Fix the User= misconfiguration that prevents the service from starting, fix incorrect dependency reference, and add crash-loop prevention.

**Dependencies:** None (independent of SurrealDB tasks)

**Files:**
- Modify: `~/.config/systemd/user/cohezion-lab.service`
- Modify: `/home/mike-anderson/dev/cohezion/systemd/cohezion-lab.service` (template)

**Key Decisions / Notes:**
- Remove `User=mike-anderson` (user services already run as the user, this causes supplementary group errors)
- Change `After=network.target surrealdb.service` to `After=network.target` (surrealdb.service doesn't exist in user scope; the system service is cohezion-surreal.service which is in a different scope)
- Change `WantedBy=multi-user.target` to `WantedBy=default.target` (correct target for user services)
- Add `StartLimitBurst=3` and `StartLimitIntervalSec=300` in `[Unit]` section
- Change `Restart=always` to `Restart=on-failure` (don't restart on clean exit)
- Note: `lab_driver.py` doesn't exist. After fixing the service config, it will still fail because the entry point is missing. The service should be **disabled** (not masked — allow future use) until `lab_driver.py` is implemented.
- Unmask after hardening: `systemctl --user unmask cohezion-lab.service`
- Then disable: `systemctl --user disable cohezion-lab.service`
- Update both the installed service and the project template in `systemd/`
- Run `systemctl --user daemon-reload`

**Definition of Done:**
- [ ] User= line removed from service file
- [ ] Dependency changed from surrealdb.service to just network.target
- [ ] WantedBy changed to default.target
- [ ] StartLimitBurst=3 and StartLimitIntervalSec=300 in [Unit] section
- [ ] Restart changed to on-failure
- [ ] Service unmasked then disabled (lab_driver.py doesn't exist)
- [ ] Project template in systemd/ updated to match

**Verify:**
- `systemctl --user cat cohezion-lab.service` shows corrected config with StartLimit in [Unit]
- `systemctl --user is-enabled cohezion-lab.service` shows `disabled`
- No more "Failed to determine supplementary groups" errors in journal

### Task 5: Clean Up Dead Service Symlinks

**Objective:** Remove broken symlinks for services that no longer exist (antiquarian, mycelium, shadow).

**Dependencies:** None

**Files:**
- Remove: `~/.config/systemd/user/cohezion-antiquarian.service` (broken symlink → deleted target)
- Remove: `~/.config/systemd/user/cohezion-mycelium.service` (broken symlink → deleted target)
- Remove: `~/.config/systemd/user/cohezion-shadow.service` (broken symlink → deleted target)

**Key Decisions / Notes:**
- These are symlinks pointing to `/home/mike-anderson/dev/cohezion/systemd/cohezion-{antiquarian,mycelium,shadow}.service` which don't exist
- `systemctl --user daemon-reload` after removal
- This eliminates "not-found" entries in systemctl status

**Definition of Done:**
- [ ] All three broken symlinks removed
- [ ] `systemctl --user daemon-reload` executed
- [ ] No "not-found" Cohezion services in `systemctl --user list-units --all`

**Verify:**
- `ls -la ~/.config/systemd/user/cohezion-{antiquarian,mycelium,shadow}.service 2>&1` shows "No such file"
- `systemctl --user list-units cohezion* --all` shows no "not-found" entries

### Task 6: Harden ngrok and Simulation Services

**Objective:** Harden ngrok-tunnel.service, review ngrok-watchdog.service (references missing script), and add restart limits to simulation service templates.

**Dependencies:** None

**Files:**
- Modify: `~/.config/systemd/user/ngrok-tunnel.service` (minor tweaks)
- Review: `~/.config/systemd/user/ngrok-watchdog.service` (references missing ngrok_watchdog.py — disable if script missing)
- Modify: `/home/mike-anderson/dev/cohezion/systemd/cohezion-simulation.service` (add restart limits to template)

**Key Decisions / Notes:**
- ngrok-tunnel: Already has `StartLimitBurst=5` and `StartLimitInterval=600` — good
- Move `StartLimitBurst` and `StartLimitInterval` from `[Service]` to `[Unit]` section (correct placement for systemd 255)
- Add `MemoryMax=512M` to ngrok-tunnel (ngrok shouldn't need more)
- Switch ngrok logs from `/tmp/ngrok_tunnel.log` to `StandardOutput=journal` (let journald handle rotation)
- ngrok-watchdog: References `scripts/ngrok_watchdog.py` which doesn't exist. Disable the watchdog timer until the script is implemented
- cohezion-simulation.service template: Add `StartLimitBurst=3` and `StartLimitIntervalSec=600` in `[Unit]` section for future installations
- Run `systemctl --user daemon-reload`

**Definition of Done:**
- [ ] ngrok-tunnel StartLimit directives in correct [Unit] section
- [ ] ngrok-tunnel MemoryMax added
- [ ] ngrok-tunnel switched to journal logging
- [ ] ngrok-watchdog.timer disabled (script doesn't exist)
- [ ] Simulation service template has restart limits in [Unit]
- [ ] daemon-reload executed

**Verify:**
- `systemctl --user cat ngrok-tunnel.service` shows correct config with StartLimit in [Unit]
- `systemctl --user show ngrok-tunnel.service -p StartLimitBurst` returns 5
- `systemctl --user is-enabled ngrok-watchdog.timer` shows `disabled`

### Task 7: Create systemd Service Guardian

**Objective:** Create a lightweight, dependency-free systemd timer + script as a SECONDARY safety net that monitors all Cohezion services for crash loops. The PRIMARY prevention is `StartLimitBurst`/`StartLimitIntervalSec` in each service's `[Unit]` section. The guardian catches edge cases: services without proper limits, slow-burn crash loops under burst thresholds, or manual restarts of failed services.

**Dependencies:** Task 3, Task 4, Task 6 (services must be hardened first)

**Files:**
- Create: `/home/mike-anderson/dev/cohezion/scripts/service_guardian.sh`
- Create: `~/.config/systemd/user/cohezion-guardian.service`
- Create: `~/.config/systemd/user/cohezion-guardian.timer`

**Key Decisions / Notes:**
- Pure bash script (no Python dependencies, no cohezion imports — survives any codebase breakage)
- Runs every 2 minutes via systemd timer (reduced from 5 for faster detection)
- Checks all cohezion-* and ngrok-* services for:
  - High restart count via `NRestarts` property (>10 since boot → alert)
  - "activating (auto-restart)" state with "Result: exit-code" → stop if user service, alert if system service
  - Disk usage in data/surrealdb/ exceeding threshold (>10K files or >1GB)
- **Privilege boundary:** Guardian runs as user service. For user services (cohezion-lab, ngrok-*), it can stop them directly. For system services (cohezion-surreal), it can only LOG alerts and send desktop notifications (cannot `systemctl stop` without sudo). This is documented and acceptable — StartLimitBurst is the primary prevention for system services.
- Add timeout to prevent guardian from hanging: `ExecStart=/usr/bin/timeout 60 /path/to/service_guardian.sh` and `TimeoutStartSec=90`
- Actions: stop runaway user services, log alerts for system services, write to syslog, send desktop notification via `notify-send`
- Script is idempotent (safe to run multiple times)
- Does NOT restart services (that's the user's job after investigation)
- The timer itself has restart limits to prevent meta-crash-loops

**Definition of Done:**
- [ ] Guardian script exists and is executable
- [ ] Guardian has timeout wrapper (60s)
- [ ] Timer fires every 2 minutes
- [ ] Guardian has no Python dependencies (pure bash + standard utils)
- [ ] Guardian logs actions to journal
- [ ] Guardian correctly handles user vs system service privilege boundary

**Verify:**
- `bash -n /home/mike-anderson/dev/cohezion/scripts/service_guardian.sh` — syntax check passes
- `bash /home/mike-anderson/dev/cohezion/scripts/service_guardian.sh` — runs without errors on healthy system
- `systemctl --user is-active cohezion-guardian.timer` shows `active`

### Task 8: Create Claude Code PreToolUse Safety Hooks

**Objective:** Create PreToolUse hooks that prevent AI coding tools from accidentally breaking services or creating runaway processes. These hooks fire before any Bash command executes in Claude Code (and can be adapted for Antigravity/Gemini CLI/OpenCode via their hook mechanisms).

**Dependencies:** None (can run in parallel with other tasks)

**Files:**
- Create: `/home/mike-anderson/dev/cohezion/.claude/hooks/guard-services.sh`
- Modify: `/home/mike-anderson/dev/cohezion/.claude/settings.local.json` (add new PreToolUse hook)

**Key Decisions / Notes:**
- Hook fires on `PreToolUse[Bash]` — intercepts all shell commands before execution
- Block patterns that could create runaway services:
  - `systemctl.*Restart=always` without `StartLimitBurst` (prevents creating unprotected services)
  - `while true` or `for ((...))` infinite loops without timeout
  - `nohup` or `&` backgrounding of processes that could outlive the session
- Warn on patterns that touch service files without proper safeguards
- Hook reads `$TOOL_INPUT` (JSON with command field) from stdin
- Exit 0 = allow, Exit 2 = block with message
- **Cross-tool portability:** Document how to adapt for Antigravity (`.antigravity/hooks/`), Gemini CLI (hook config), and OpenCode
- The existing `settings.local.json` already has hook infrastructure (`PreToolUse[Bash]` matcher for `warn-sensitive-commands.sh`, but that file doesn't exist). We should create the missing file AND add our new hook.

**Definition of Done:**
- [ ] guard-services.sh hook exists and is executable
- [ ] Hook blocks `Restart=always` without `StartLimitBurst` in service file writes
- [ ] Hook warns on `while true` / infinite loop patterns
- [ ] settings.local.json updated with new hook entry
- [ ] Documentation comment in hook explaining cross-tool adaptation

**Verify:**
- `bash -n /home/mike-anderson/dev/cohezion/.claude/hooks/guard-services.sh` — syntax check passes
- Hook correctly blocks a test pattern (simulated dangerous command)

### Task 9: Integrate with Healing System and Add Structured Logging

**Objective:** Wire the guardian's findings into Cohezion's self-healing system so crash-loop detection feeds back into compound engineering knowledge. Add structured JSON logging for all guardian actions.

**Dependencies:** Task 7 (guardian must exist)

**Files:**
- Create: `/home/mike-anderson/dev/cohezion/scripts/guardian_reporter.py` (lightweight reporter)
- Modify: `/home/mike-anderson/dev/cohezion/scripts/service_guardian.sh` (add JSON log output)

**Key Decisions / Notes:**
- Guardian (bash) writes JSON events to `/home/mike-anderson/dev/cohezion/data/guardian_events.jsonl`
- Each event: `{"timestamp": "...", "service": "...", "event": "crash_loop|high_restarts|disk_alert", "action": "stopped|alert", "restarts": N, "details": "..."}`
- `guardian_reporter.py` is a separate lightweight Python script that:
  - Reads `guardian_events.jsonl`
  - Registers events with the healing system (`cohezion.healing.HealthStatus`)
  - Can be run periodically or on-demand
  - This keeps the guardian itself dependency-free (pure bash) while still feeding the compound loop
- Add structured logging to guardian: each check writes a JSON line even when healthy (for dashboarding)
- Token efficiency: events are JSONL (one line per event, easily grep-able, no full JSON parse needed)

**Definition of Done:**
- [ ] Guardian writes JSON events to guardian_events.jsonl
- [ ] guardian_reporter.py reads events and logs to healing system
- [ ] Both healthy and alert states are logged
- [ ] Events are parseable with standard tools (`jq`, `grep`)

**Verify:**
- `bash /home/mike-anderson/dev/cohezion/scripts/service_guardian.sh` produces JSONL output
- `jq . /home/mike-anderson/dev/cohezion/data/guardian_events.jsonl` parses successfully
- `uv run python scripts/guardian_reporter.py` runs without errors

### Task 10: Bring Services Online and Verify

**Objective:** Start all services, verify SurrealDB is healthy, confirm no crash loops, and run a smoke test.

**Dependencies:** Task 1, Task 2, Task 3, Task 4, Task 5, Task 6, Task 7, Task 8, Task 9

**Files:**
- No new files

**Key Decisions / Notes:**
- Start order: cohezion-surreal → verify SurrealDB responds → start ngrok → start guardian timer
- cohezion-lab stays disabled (no entry point)
- Verify SurrealDB: attempt connection with `surreal sql` or health endpoint
- **SURREAL_PASS**: Now a static token in .env. Source .env to get the password for client connections.
- Watch journal for 60 seconds to confirm no crash-loop restarts
- Verify guardian timer is running and has fired at least once
- **Protocol verification**: If rocksdb:// was configured, verify SurrealDB started without errors. If it fails, revert to file:// as documented in Task 3.

**Definition of Done:**
- [ ] cohezion-surreal.service is active and running (not masked)
- [ ] SurrealDB responds to queries
- [ ] ngrok-tunnel.service is active (or stopped cleanly if no tunnel needed)
- [ ] cohezion-guardian.timer is active and waiting
- [ ] No services in crash loop (journal clean for 60 seconds)
- [ ] cohezion-lab.service is disabled (documented: needs lab_driver.py)

**Verify:**
- `systemctl is-active cohezion-surreal.service` shows `active`
- `journalctl -u cohezion-surreal.service --since "1 minute ago" --no-pager` shows healthy startup, no errors
- `systemctl --user is-active cohezion-guardian.timer` shows `active`
- `systemctl --user list-units cohezion* ngrok* --all --no-pager` shows no "failed" or "activating" units

## Testing Strategy

- **Task 1:** Manual SurrealDB start test validates DB recovery. If DB is unrecoverable, fresh init.
- **Task 2:** Manual verification (file cleanup, journal vacuum)
- **Task 3-6:** `systemctl show` to verify service properties match expected values. Confirm StartLimit in [Unit] section via `systemctl cat`.
- **Task 7:** Syntax check (`bash -n`), dry-run execution, verify timer activation
- **Task 8:** End-to-end: start services → watch journal → verify health → confirm guardian detects nothing wrong

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| MANIFEST-190909 is also corrupt or references missing SST files | Medium | High | Validate DB immediately in Task 1 (not Task 8). If validation fails, reinitialize with fresh DB — dev data is expendable |
| rocksdb:// protocol behaves differently from file:// | Low | Medium | Test separately: first verify file:// works, then switch to rocksdb://. Two verification points, not one combined change |
| MemoryMax=16G triggers OOM-kill of SurrealDB (66GB block cache) | Medium | Low | OOM-kill + StartLimitBurst=5 = at most 5 OOM kills in 10 min, then stop. Far better than infinite crash loop. SurrealDB 2.4.1 doesn't expose RocksDB block_cache_size tuning. Monitor empirically after startup |
| Service guardian false-positives | Medium | Low | Guardian only STOPS user services, never restarts. For system services, alert only. False-positive = service stopped, user investigates. Safe default |
| Guardian script hangs (systemd overloaded) | Low | Low | ExecStart wraps script with `/usr/bin/timeout 60`. TimeoutStartSec=90 in service unit. Prevents accumulation of blocked instances |
| Accidental service re-enable during implementation | Low | Medium | Services masked in Task 1, unmasked only after hardening in Task 3/4. Prevents reboot from restarting unhardened services |

## Open Questions

- None — all questions resolved during investigation and plan verification

### Deferred Ideas

- Rewrite `DaemonManager` and `wake_up.py` to use systemd commands instead of custom process management
- Research if SurrealDB has a config file or env var to set RocksDB block_cache_size explicitly (would eliminate the MemoryMax OOM risk)
- Add Prometheus/Grafana monitoring for long-term observability
- Create a `/wake` skill that integrates with the guardian for AI-tool-aware service management
- Move cohezion-surreal.service from system scope to user scope (it already runs as mike-anderson, no need for system service)
- Add polkit rule to allow user to stop system services without sudo (alternative to scope migration)
