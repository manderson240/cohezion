---
name: claude-code-plugin-removal
description: |
  Complete multi-layer cleanup for removing a misbehaving Claude Code plugin.
  Use when: (1) a plugin causes session startup timeout (30s connection failure),
  (2) plugin crashes with config errors on every session start,
  (3) a plugin is redundant and you want to remove it cleanly.
  Key insight: plugin state lives in 4 separate locations that must ALL be cleaned.
author: Claude Code
version: 1.0.0
---

# Claude Code Plugin Removal

## Problem

A Claude Code plugin crashes on startup every session, causing a 30-second connection
timeout. Or a plugin is redundant and needs to be cleanly removed. Simply deleting
the plugin directory is insufficient — state persists in 4 separate locations.

## Context / Trigger Conditions

- Session start shows MCP connection timeout for a specific plugin
- Error like `SerenaConfigError: key not found in configuration` in MCP logs
- Want to remove a plugin that duplicates built-in capabilities
- Plugin logs at: `~/.cache/claude-cli-nodejs/<project-hash>/mcp-logs-plugin-<name>-<name>/`

## Solution

### Step 1: Diagnose (optional)

Check the plugin's MCP logs to understand the failure:

```bash
# Find the log directory
ls ~/.cache/claude-cli-nodejs/*/mcp-logs-plugin-<name>-<name>/
# View the most recent log
tail -50 ~/.cache/claude-cli-nodejs/*/mcp-logs-plugin-<name>-<name>/*.jsonl | jq .
```

**Fix vs Remove decision:**
- Fix: if the plugin has unique value and the config issue is trivial
- Remove: if capabilities are already covered by built-in tools (LSP, vexor, Grep)

### Step 2: Remove from plugin registry

```bash
# View current plugins
cat ~/.claude/plugins/installed_plugins.json | python3 -c "import sys,json; data=json.load(sys.stdin); [print(k) for k in data['plugins']]"

# Remove the plugin entry programmatically
python3 -c "
import json
with open('$HOME/.claude/plugins/installed_plugins.json') as f:
    data = json.load(f)
key = '<plugin-name>@claude-plugins-official'  # adjust as needed
if key in data['plugins']:
    del data['plugins'][key]
    with open('$HOME/.claude/plugins/installed_plugins.json', 'w') as f:
        json.dump(data, f, indent=2)
    print('Removed', key)
else:
    print('Not found:', key)
"
```

### Step 3: Remove plugin config directory

```bash
rm -rf ~/.<plugin-name>/
# e.g.: rm -rf ~/.serena/
```

### Step 4: Clean up cached MCP logs

```bash
rm -rf ~/.cache/claude-cli-nodejs/*/mcp-logs-plugin-<name>-<name>/
```

### Step 5: Clean up source code references (if project tracks the plugin)

Search for references in the project's MCP registry and docstrings:

```bash
grep -ri "<plugin-name>" src/ --include="*.py" --include="*.json" -l
```

For each file found, remove the plugin's entry from:
- `mcp_registry.json` — remove from the `external` array, fix trailing commas
- `__init__.py` docstrings — remove from the listed external servers
- `registry.py` docstrings — update class docstring

### Step 6: Verify complete removal

```bash
# 1. Not in plugin registry
grep -i "<plugin-name>" ~/.claude/plugins/installed_plugins.json && echo "FOUND (BAD)" || echo "GONE"

# 2. Not in project MCP configs
grep -ri "<plugin-name>" .mcp.json mcp_servers.json 2>/dev/null && echo "FOUND" || echo "GONE"

# 3. Not in source code (binary .pyc files are harmless, ignore them)
grep -ri "<plugin-name>" src/ --include="*.py" --include="*.json"

# 4. Config directory gone
ls ~/.<plugin-name>/ 2>/dev/null && echo "EXISTS (BAD)" || echo "GONE"

# 5. Cached logs gone
ls ~/.cache/claude-cli-nodejs/*/mcp-logs-plugin-<plugin-name>-<plugin-name>/ 2>/dev/null && echo "EXISTS (BAD)" || echo "GONE"
```

## Verification

- Start a new Claude Code session — the 30-second timeout should be gone
- Run tests to confirm no breakage from registry/source changes: `uv run pytest tests/ -q`

## Example: Serena Removal (2026-03-10)

Serena crashed with `SerenaConfigError: 'projects' key not found` on every session.
Its capabilities (code navigation, semantic search) were fully covered by Claude Code's
built-in LSP, vexor, and Grep tools.

```bash
# Plugin key in installed_plugins.json
"serena@claude-plugins-official"

# Config dir
rm -rf ~/.serena/

# Cached logs (multiple project hashes)
rm -rf ~/.cache/claude-cli-nodejs/*/mcp-logs-plugin-serena-serena/

# Source refs removed from:
# src/cohezion/mcp/mcp_registry.json         (external array entry)
# src/cohezion/mcp/__init__.py               (docstring)
# src/cohezion/mcp/registry.py               (class docstring)
# src/cohezion-archive/mcp/mcp_registry.json (same)
# src/cohezion-archive/mcp/__init__.py       (same)
# src/cohezion-archive/mcp/registry.py       (same)
```

Result: 4020 tests passed, no regressions, no more startup timeout.

## Bulk Namespace Deduplication (Multiple Duplicate Plugins)

When the same skills appear under multiple namespace prefixes (e.g., `claude-api:*`,
`document-skills:*`, `example-skills:*` all providing identical pdf/docx/pptx skills),
remove all but one canonical namespace:

```python
import json

path = f"{os.path.expanduser('~')}/.claude/plugins/installed_plugins.json"
with open(path) as f:
    data = json.load(f)

# Remove duplicate namespaces, keep the canonical one
to_remove = ['claude-api@anthropic-agent-skills', 'example-skills@anthropic-agent-skills']
# keep: 'document-skills@anthropic-agent-skills'

for key in to_remove:
    if key in data['plugins']:
        del data['plugins'][key]

with open(path, 'w') as f:
    json.dump(data, f, indent=2)
```

Plugin registry structure: `{"version": int, "plugins": {"name@marketplace": {...}}}`

## Notes

- `.pyc` bytecode files in `__pycache__/` may still contain old strings — safe to ignore,
  they regenerate automatically on next import with updated source
- The `~/.claude/plugins/installed_plugins.json` file also controls which plugin cache
  directories get loaded — removing the entry here is the most important step
- If the plugin has no source code references in the project, only Steps 2-4 are needed
- Removals from `installed_plugins.json` may be reverted by marketplace syncs or session
  restarts — keep a `.bak` file and re-apply if needed:
  `cp installed_plugins.json installed_plugins.json.bak.$(date +%Y%m%d)`
