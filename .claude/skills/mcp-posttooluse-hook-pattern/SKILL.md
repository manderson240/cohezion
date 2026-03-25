---
name: mcp-posttooluse-hook-pattern
description: |
  Pattern for creating PostToolUse hooks that trigger on MCP tool calls (not just native Claude Code tools).
  Use when: (1) you need automation that fires after an MCP tool completes (e.g., vault_write, vault_edit),
  (2) hook runs Python code that imports project dependencies but silently fails,
  (3) hook exits 0 but produces no effect. Critical pitfall: hooks run with system Python which
  lacks project venv dependencies like httpx. Must use venv Python explicitly.
author: Claude Code
version: 1.0.0
---

# MCP PostToolUse Hook Pattern

## Problem

You want a Claude Code hook that fires after an MCP tool call (e.g., `vault_write`), but:
- Most hook examples only show matching native tools (`Edit`, `Write`, `Bash`)
- Your hook imports project dependencies that aren't available in system Python
- The hook exits 0 but silently does nothing

## Trigger Conditions

- Need automation after MCP tool calls complete
- Hook works when tested manually with venv Python but fails silently in Claude Code
- `python3 -c "import httpx"` fails but `.venv/bin/python3 -c "import httpx"` works

## Solution

### 1. Settings.json Registration

MCP tool names use double-underscore format. Use pipe for multiple matchers:

```json
{
  "PostToolUse": [
    {
      "matcher": "mcp__cohezion-vault__vault_write|mcp__cohezion-vault__vault_edit",
      "hooks": [
        {
          "type": "command",
          "command": ".claude/hooks/my-hook.sh"
        }
      ]
    }
  ]
}
```

### 2. Hook Stdin Format

The hook receives JSON on stdin with these fields:

```json
{
  "tool_name": "mcp__cohezion-vault__vault_write",
  "tool_input": {"path": "cortex/my-note.md", "content": "..."},
  "tool_result": "Written: cortex/my-note.md"
}
```

Extract fields with Python (system python3 has json):

```bash
INPUT=$(cat)
PATH_VAL=$(echo "$INPUT" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    print(d.get('tool_input', {}).get('path', ''))
except Exception:
    print('')
" 2>/dev/null)
```

### 3. Venv Python for Project Dependencies

**This is the critical pitfall.** Hooks run with system Python, not the project venv. If your hook imports project packages (httpx, pydantic, etc.), it will silently fail.

```bash
# Use the project venv Python explicitly
VENV_PYTHON="$HOME/dev/project/.venv/bin/python3"
[ -x "$VENV_PYTHON" ] || VENV_PYTHON="python3"  # Fallback

"$VENV_PYTHON" -c "
import sys, os
sys.path.insert(0, os.path.expanduser('~/dev/project/src'))
from my_module import my_function
# ... use project code ...
" 2>/dev/null
```

### 4. Non-Blocking Pattern

Hooks must never block the tool that triggered them. Always exit 0:

```bash
# All Python code wrapped in try/except, stderr redirected
"$VENV_PYTHON" -c "..." 2>/dev/null
exit 0  # Always exit 0 regardless of Python success
```

## Verification

Test the hook manually by piping simulated JSON:

```bash
echo '{"tool_name":"mcp__server__tool","tool_input":{"path":"test.md"}}' | .claude/hooks/my-hook.sh
echo "Exit: $?"  # Should be 0
```

## Example

See `.claude/hooks/graph-sync-on-vault-write.sh` for a complete working example that:
- Matches `vault_write` and `vault_edit` MCP tools
- Extracts the vault path from tool_input
- Uses venv Python to call `graph_writer.upsert_neuron()`
- Skips noisy paths (daily/, sessions/)
- Always exits 0
