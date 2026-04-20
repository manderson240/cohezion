# Troubleshooting Guide

Quick fixes for common issues with pi-coding-agent 0.67.2+ features.

## Installation Issues

### Wrong Pi Version

```bash
# Check current version
npm list @mariozechner/pi-coding-agent

# Should show: @mariozechner/pi-coding-agent@0.67.2

# Update if needed
npm install @mariozechner/pi-coding-agent@^0.67.2
```

### Missing Dependencies

```bash
# Reinstall from package.json
npm install

# Or force update
npm update @mariozechner/pi-coding-agent
```

## Keybindings Issues

### Super Key Not Working

**Problem:** `super+k`, `super+enter` don't respond

**Solutions:**

```bash
# 1. Verify terminal receives super key (Kitty)
kitty +kitten show_key -m super
# Type a key, should show: super+k

# 2. Check keybindings loaded
# In Pi: /settings → scroll to keybindings

# 3. Reload keybindings
/reload

# 4. Verify config format
python3 -m json.tool .pi/keybindings.json
```

### Keybindings Not Loading

```bash
# Check settings.json references keybindings file
cat .pi/settings.json | grep -A1 '"keybindings"'

# Expected output:
# "keybindings": ".pi/keybindings.json"

# Verify file exists
ls -la .pi/keybindings.json

# Check JSON validity
python3 -c "import json; json.load(open('.pi/keybindings.json'))"
```

### Conflicts with OS Shortcuts

| Shortcut | Conflict | Solution |
|----------|----------|----------|
| `super+n` | New window | Use `ctrl+shift+n` or `super+shift+n` |
| `super+enter` | Maximize | Use `ctrl+enter` |
| `super+o` | Open file | Use `ctrl+o` |

## --append-system-prompt Issues

### Prompts Not Appending

```bash
# ❌ Wrong: Args after prompt
pi "my prompt" --append-system-prompt "context"

# ✅ Correct: Flags before prompt
pi --append-system-prompt "context" "my prompt"
```

### Special Characters

```bash
# ❌ Broken: Unescaped quotes
pi --append-system-prompt "Say "hello""

# ✅ Fixed: Use single quotes
pi --append-system-prompt 'Say "hello"'

# ✅ Or escape
pi --append-system-prompt "Say \"hello\""
```

### Too Many Appends

```bash
# Check if hitting context limits
pi --verbose --append-system-prompt "..." 2>&1 | grep "context"

# Consider using skill files instead for large context
echo "Large context" > .pi/skills/my-context/SKILL.md
```

## SDK/Extension Issues

### TypeScript Errors

```bash
# Install dependencies
npm install @sinclair/typebox

# Or use tsx for execution
uv run tsx .pi/examples/sdk-embedded.ts

# Check TypeScript version
tsc --version  # Should be 5.0+
```

### Extension Not Loading

```bash
# Enable verbose mode
PI_VERBOSE=1 uv run tsx .pi/examples/sdk-embedded.ts

# Check extension count in output
grep -i "extension" <<< "$output"
```

### Event Handlers Not Firing

```typescript
// ❌ Wrong: Missing await in async handler
pi.on("agent_start", (event, ctx) => {
  doSomething(); // Async not awaited
});

// ✅ Correct: Mark handler as async
pi.on("agent_start", async (event, ctx) => {
  await doSomething();
});
```

### Tool Registration Errors

```typescript
// ❌ Wrong: Type mismatch
import { Type } from "@sinclair/typebox";

parameters: Type.Object({
  count: Type.Integer(),
}),
execute: async (id, params) => {
  // params.count is number, not string
  const x = params.count + "items"; // ❌
}

// ✅ Correct: Type-safe usage
execute: async (id, params) => {
  const items = new Array(params.count).fill("item"); // ✅
}
```

## Wrapper Script Issues

### pi-cohezion.sh Not Executable

```bash
# Fix permissions
chmod +x pi-cohezion.sh

# Test execution
./pi-cohezion.sh --help
```

### Array Syntax Errors

```bash
# If using older bash, arrays might not work
bash --version  # Should be 4.0+

# Alternative: Use strings
APPEND_FLAGS="--append-system-prompt 'ctx1' --append-system-prompt 'ctx2'"
eval pi $APPEND_FLAGS "$@"
```

## Configuration Issues

### Settings Not Loading

```bash
# Verify settings.json is valid JSON
python3 -m json.tool .pi/settings.json > /dev/null && echo "Valid JSON"

# Check for trailing commas (not allowed in JSON)
grep -E ',$' .pi/settings.json  # Should return nothing

# Validate structure
python3 -c "
import json
with open('.pi/settings.json') as f:
    data = json.load(f)
    print('Has extensions:', 'extensions' in data)
    print('Has keybindings:', 'keybindings' in data)
"
```

### Extensions Not Loading

```bash
# List configured extensions
cat .pi/settings.json | jq '.extensions'

# Verify files exist
for ext in .pi/extensions/*.ts; do
  [ -f "$ext" ] && echo "✓ $ext" || echo "✗ $ext missing"
done

# Check TypeScript compilation
npx tsc --noEmit .pi/extensions/*.ts 2>&1 | head -20
```

## Performance Issues

### Slow Startup

```bash
# Profile startup time
time pi --version

# Disable telemetry (already disabled in settings)
export PI_TELEMETRY=0

# Check for heavy extensions
ls -la .pi/extensions/*.ts  # Large files slow loading
```

### High Memory Usage

```bash
# Monitor with PI_TUI_WRITE_LOG
export PI_TUI_WRITE_LOG="/tmp/pi-logs"
pi

# Check log sizes
ls -lah /tmp/pi-logs/

# Clear old sessions
pi /session  # Then delete old sessions
```

## Session Issues

### Session Fork Fails

```bash
# ✅ 0.60.0+ supports CLI forking
pi --fork /path/to/session.jsonl

# Check session file exists
ls -la ~/.pi/agent/sessions/*.jsonl | head -5

# Fork by partial ID
pi --fork abc123  # Matches any session starting with abc123
```

### Session Import/Export

```bash
# Export to JSONL
/export ~/backups/session-$(date +%Y%m%d).jsonl

# Import from JSONL
/import ~/backups/session-20260415.jsonl

# Verify JSONL format
head -5 ~/backups/session-*.jsonl | jq .type
```

## Getting Help

### Collect Diagnostic Info

```bash
#!/bin/bash
# collect-diagnostics.sh

echo "=== Pi Version ==="
npm list @mariozechner/pi-coding-agent 2>/dev/null

echo "=== Node Version ==="
node --version

echo "=== Settings ==="
cat .pi/settings.json | jq 'del(.hooks)'  # Remove sensitive hooks

echo "=== Keybindings ==="
python3 -m json.tool .pi/keybindings.json

echo "=== Extensions ==="
ls -la .pi/extensions/

echo "=== Environment ==="
env | grep -E "^(PI_|COHEZION)" | sort
```

### Debug Mode

```bash
# Enable all verbose logging
PI_VERBOSE=1 PI_DEBUG=1 pi

# TUI debug logs
mkdir -p /tmp/pi-debug
PI_TUI_WRITE_LOG=/tmp/pi-debug pi
```

## Reference: Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | General error |
| 2 | Invalid arguments |
| 3 | Configuration error |
| 130 | Interrupted (Ctrl+C) |

## See Also

- [Quick Start](00_QUICKSTART.md)
- [Keybindings Guide](01_KEYBINDINGS.md)
- [SDK Extensions Guide](02_SDK_EXTENSIONS.md)
- [Pi Docs](https://github.com/badlogic/pi-mono/tree/main/pi/packages/coding-agent/docs)

---
*Part of the Cohezion Pi Setup - Last updated: 2026-04-15*
