---
name: systemd-crash-loop-prevention
description: |
  Harden systemd services to prevent infinite crash loops and resource exhaustion.
  Use when: (1) service is crash-looping, (2) hardening new services, (3) seeing
  "Start request repeated too quickly" errors. Critical gotchas: StartLimitBurst
  MUST be in [Unit] section (systemd 255+), EnvironmentFile= doesn't evaluate shell
  commands (reads $(command) literally).
author: Claude Code
version: 1.0.0
---

# systemd Crash-Loop Prevention

## Problem

Services with `Restart=always` and no limits can crash-loop infinitely, consuming resources and cascading to system instability. Example: 129K+ restarts over 4 days from a single corrupted database file crashed journald and destabilized the desktop.

## Context / Trigger Conditions

**Use when:**
- Service is crash-looping (check with `systemctl show <service> -p NRestarts`)
- Creating new systemd services that should auto-restart
- Seeing "Start request repeated too quickly" errors
- After fixing a service crash, adding safeguards

## Solution

### Step 1: Add Restart Limits (PRIMARY Prevention)

**⚠️ CRITICAL: StartLimitBurst and StartLimitIntervalSec MUST be in [Unit] section.**

On systemd 255+, these directives are silently ignored if placed in [Service].

```ini
[Unit]
Description=My Service
After=network.target
StartLimitBurst=5
StartLimitIntervalSec=600

[Service]
Type=simple
ExecStart=/path/to/binary
Restart=on-failure
RestartSec=30
```

**Parameters:**
- `StartLimitBurst=5` — max 5 restarts
- `StartLimitIntervalSec=600` — in a 10-minute window
- `Restart=on-failure` — only restart on crashes (not clean exits)
- `RestartSec=30` — wait 30s between restart attempts (reduces churn)

### Step 2: Add Resource Limits

Prevent runaway resource consumption:

```ini
[Service]
MemoryMax=16G
CPUQuota=200%
TasksMax=256
```

### Step 3: Add Health Checks

Validate preconditions before starting:

```ini
[Service]
ExecStartPre=/bin/bash -c 'test -f /path/to/required/file'
ExecStartPre=/bin/bash -c 'command-to-check-database-health'
```

### Step 4: Fix Environment Variable Shell Substitution

**⚠️ GOTCHA: systemd EnvironmentFile= doesn't evaluate shell commands.**

**Broken:**
```bash
# .env
PASSWORD=$(python3 -c "import secrets; print(secrets.token_urlsafe(24))")
```

systemd reads this as the literal string `$(python3 ...)`, NOT the evaluated result.

**Fixed:**
```bash
# Generate once, write static value
NEW_PASS=$(python3 -c "import secrets; print(secrets.token_urlsafe(24))")
sed -i "s|^PASSWORD=.*|PASSWORD=${NEW_PASS}|" .env
```

### Step 5: Reload and Verify

```bash
sudo systemctl daemon-reload
systemctl show <service> -p StartLimitBurst,StartLimitIntervalSec,MemoryMax
```

**Expected output:**
```
StartLimitBurst=5
StartLimitIntervalUSec=10min
MemoryMax=17179869184
```

## Verification

1. **Check restart limits are in [Unit]:**
   ```bash
   systemctl cat <service> | grep -A2 "\[Unit\]"
   ```

2. **Trigger a crash and verify it stops after burst limit:**
   ```bash
   # Force crash 6 times
   systemctl show <service> -p NRestarts  # Should be ≤5
   systemctl is-active <service>          # Should be "failed" after 5 crashes
   ```

3. **Check journald logs don't show infinite restarts:**
   ```bash
   journalctl -u <service> --since "1 hour ago" | grep -c "Started\|Stopped"
   ```

## Example: Real-World Cascade

**Before hardening:**
1. SurrealDB MANIFEST file corrupted
2. Service crashed every 5 seconds (`Restart=always`, no limits)
3. 129,220 restarts over 4 days
4. journald overwhelmed (1.2GB logs) → journald crashed
5. Desktop portal crashed from system instability

**After hardening:**
- `StartLimitBurst=5` in [Unit] → max 5 crashes in 10 minutes
- `RestartSec=30` → less aggressive restart
- `MemoryMax=16G` → can't consume all RAM
- `ExecStartPre` → validates MANIFEST file exists before starting

Result: Any future corruption stops after 5 attempts instead of 129K.

## Common Mistakes

1. **Placing StartLimitBurst in [Service] instead of [Unit]** — silently ignored on systemd 255+
2. **Using shell substitution in .env files** — systemd reads literals, not evaluated results
3. **Restart=always instead of on-failure** — restarts even on clean exits
4. **No ExecStartPre validation** — crashes repeatedly on same missing dependency
5. **RestartSec too low** — creates restart churn

## References

- systemd.unit(5) — StartLimitBurst, StartLimitIntervalSec
- systemd.service(5) — Restart, RestartSec
- systemd.exec(5) — MemoryMax, CPUQuota
