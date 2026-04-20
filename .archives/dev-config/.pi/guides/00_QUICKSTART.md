# Cohezion Pi Quick Start Guide

Get up and running with the new pi-coding-agent 0.67.2+ features in 5 minutes.

## Prerequisites

```bash
# Verify pi-coding-agent version
cd /home/mike-anderson/dev/cohezion
npm list @mariozechner/pi-coding-agent
# Should show: @mariozechner/pi-coding-agent@0.67.2
```

## 5-Minute Walkthrough

### Step 1: Start Interactive Session with Cohezion Context (1 min)

```bash
# Option A: Use the wrapper script (recommended)
./pi-cohezion.sh

# Option B: Direct pi with multiple --append-system-prompt flags
pi --append-system-prompt "You are in the Cohezion project" \
   --append-system-prompt "Use uv, never pip" \
   --append-system-prompt "Follow FLUME-First pattern"
```

**What happens:** Each `--append-system-prompt` value is appended to the system prompt with double newlines separating them.

### Step 2: Test Kitty Super-Modified Keybindings (1 min)

**In Kitty terminal:**
- Press `super+n` → Start new session
- Press `super+t` → Open session tree
- Press `super+k` → Cancel/abort
- Press `super+enter` → Submit message

**Note:** Super = Cmd on macOS, Win key on Windows/Linux

Configure Kitty in `~/.config/kitty/kitty.conf`:
```
macos_option_as_alt no
```

### Step 3: Verify Settings Loaded (1 min)

In the Pi interactive session:
```
/settings
```

Check that:
- ✓ Extensions show: cohezion-kg.ts, cohezion-bridge-v3.ts, ci-sentinel.ts
- ✓ Keybindings file: .pi/keybindings.json
- ✓ Telemetry: disabled

### Step 4: Test SDK Inline Extension Factory (2 min)

```bash
# Run the embedded SDK example
uv run tsx .pi/examples/sdk-embedded.ts
```

Expected output:
```
=== Cohezion Embedded SDK Example ===
Extensions loaded: 2
Custom commands: /cohezion-status
Session configured with inline extension factories!
```

### Step 5: View Complete Feature History (Optional)

```bash
# Read the comprehensive release history
cat .pi/RELEASE_HISTORY.md

# Or view 0.67.2 specific features
cat .pi/FEATURES_0.67.2.md
```

## Next Steps

- [Keybindings Guide](01_KEYBINDINGS.md) - Customize keyboard shortcuts
- [SDK Extensions Guide](02_SDK_EXTENSIONS.md) - Build embedded integrations
- [Multi-Prompt Workflow](03_MULTI_PROMPT.md) - Layer context with --append-system-prompt
- [Troubleshooting](99_TROUBLESHOOTING.md) - Common issues and fixes

## Verification Checklist

- [ ] Pi version is 0.67.2+
- [ ] Wrapper script runs without errors
- [ ] Keybindings file is valid JSON
- [ ] SDK example executes successfully
- [ ] Extensions load in /settings

---
*Part of the Cohezion Pi Setup - Last updated: 2026-04-15*
