---
name: dynamic-autocompact-calibration
description: |
  Calibrate Claude Code's auto-compact threshold dynamically at session start based on
  free RAM and model context window. Use when: (1) auto-compact fires too early (losing
  context on a beefy machine); (2) auto-compact fires too late (session OOMs or slows);
  (3) sessions on machines with variable RAM load (ML training running, etc.).
  Key non-obvious fact: CLAUDE_AUTOCOMPACT_PCT_OVERRIDE is read from settings.json at
  session LAUNCH — a SessionStart hook can only affect the NEXT session's threshold.
author: Claude Code
version: 1.0.0
---

# Dynamic Auto-Compact Calibration

## Problem

`CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` set statically in settings.json is wrong for most
conditions:
- Set too high (92%) on a memory-pressured system → session slows before compaction
- Set too low (70%) on a machine with 100+ GiB free → wastes context unnecessarily

RAM availability changes session-to-session (ML training in background, other models loaded).

## Key Non-Obvious Fact

`CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` is an **env var read at session launch**, not a live config.
A SessionStart hook that modifies settings.json only affects the *next* session. This is fine —
the hook calibrates once per session start, so the value is always correct for the current conditions
by the time the next session begins. Think of it as "compute the right value for the upcoming
session, not the current one."

## Solution

### 1. Create the calibration hook

`~/.claude/hooks/autocompact-calibrate.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
SETTINGS="$HOME/.claude/settings.json"

# MemAvailable = free + reclaimable caches — best estimate for "usable"
free_gib=$(awk '/^MemAvailable:/ { printf "%.0f", $2/1024/1024 }' /proc/meminfo 2>/dev/null || echo "40")

if   [ "$free_gib" -gt 80 ]; then threshold=92
elif [ "$free_gib" -gt 60 ]; then threshold=88
elif [ "$free_gib" -gt 40 ]; then threshold=85
elif [ "$free_gib" -gt 20 ]; then threshold=80
else                               threshold=72
fi

current=$(python3 -c "
import json, sys
try:
    d = json.load(open('$SETTINGS'))
    print(d.get('env', {}).get('CLAUDE_AUTOCOMPACT_PCT_OVERRIDE', 'unset'))
except Exception:
    print('error')
" 2>/dev/null || echo "error")

if [ "$current" != "$threshold" ]; then
    python3 - <<PYEOF
import json
path = "$SETTINGS"
threshold = $threshold
with open(path) as f:
    settings = json.load(f)
settings.setdefault("env", {})["CLAUDE_AUTOCOMPACT_PCT_OVERRIDE"] = str(threshold)
with open(path, "w") as f:
    json.dump(settings, f, indent=2)
PYEOF
    echo "[autocompact:calibrated] ${free_gib}GiB free → ${threshold}% (was ${current}%). Takes effect next session."
else
    echo "[autocompact:ok] ${free_gib}GiB free → ${threshold}% already correct."
fi
```

### 2. Make executable
```bash
chmod +x ~/.claude/hooks/autocompact-calibrate.sh
```

### 3. Register in settings.json hooks.SessionStart
```json
{
  "matcher": "all",
  "hooks": [
    {
      "type": "command",
      "command": "/home/mike-anderson/.claude/hooks/autocompact-calibrate.sh",
      "async": true
    }
  ]
}
```

`async: true` — runs in background, doesn't delay session startup.

### 4. Remove hardcoded value from settings.json env block
Remove `"CLAUDE_AUTOCOMPACT_PCT_OVERRIDE": "92"` from the `env` block in settings.json.
The hook now owns this value.

## RAM → Threshold Mapping

| Free RAM     | Threshold | Rationale |
|-------------|-----------|-----------|
| > 80 GiB    | 92%       | Plenty — maximize context continuity |
| 60–80 GiB   | 88%       | Normal load |
| 40–60 GiB   | 85%       | Moderate pressure |
| 20–40 GiB   | 80%       | Tight — compact earlier |
| < 20 GiB    | 72%       | Very tight — compact aggressively |

Note: `MemAvailable` (not `MemFree`) is the right metric — includes reclaimable caches.

## Verification

After hook fires, check settings.json:
```bash
python3 -c "import json; d=json.load(open('~/.claude/settings.json')); print(d['env']['CLAUDE_AUTOCOMPACT_PCT_OVERRIDE'])"
```

Should match the RAM-calibrated value for your current system state.

## References

- `~/.claude/settings.json` — `env.CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` (the controlled key)
- `~/.claude/hooks/autocompact-calibrate.sh` — implementation
- `/proc/meminfo` — `MemAvailable` is the correct free-RAM metric (not `MemFree`)
