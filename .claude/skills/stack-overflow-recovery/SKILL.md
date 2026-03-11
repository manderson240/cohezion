---
name: stack-overflow-recovery
description: |
  Fix Claude Code crash: "Maximum call stack size exceeded" (Node.js stack overflow).
  Use when: (1) Claude Code crashes with RangeError/stack overflow (NOT heap OOM),
  (2) settings.local.json has 50+ permission entries, (3) rapid tool sequences cause
  crashes, (4) you see __NEW_LINE_* or shell fragment entries in settings.local.json.
  Root cause: permission pattern matcher recurses through every entry per tool call;
  100+ entries + rapid sequences = call stack exhaustion.
author: Claude Code
version: 1.0.0
---

# Stack Overflow Recovery — Claude Code Permission Bloat

## Problem

Claude Code (Node.js) crashes with "Maximum call stack size exceeded" — a call stack overflow in the CLI's permission/hook processing engine. **Distinct from OOM (heap limit)** — see `oom-recovery` for that.

**Root causes (three compound):**
1. `settings.local.json` permission entries balloon from `__NEW_LINE_*` junk auto-generated when approving multi-line bash commands
2. PostToolUse hooks with expensive `grep -rl` scans run in parallel during rapid tool sequences
3. Each permission entry requires pattern matching on every tool call; 150+ entries × rapid calls = stack exhaustion

## Diagnosis

```bash
# Count permission entries (> 50 is yellow, > 100 is red)
python3 -c "import json; print(len(json.load(open('.claude/settings.local.json'))['permissions']['allow']))"

# Check for junk entries
grep -c '__NEW_LINE_' .claude/settings.local.json
grep -c '"Bash(do)"' .claude/settings.local.json
grep -c '"Bash(then)"' .claude/settings.local.json
```

**Junk entry types to look for:**
- `__NEW_LINE_<hash>` — auto-generated when approving multi-line bash. Each approval spawns one per newline. Never matches again.
- Shell fragments: `Bash(do)`, `Bash(then)`, `Bash(fi)`, `Bash(done)`, `Bash(for f in *.md)`, etc.
- One-off temp scripts: `Bash(/tmp/debug_query.py:*)` — fine to remove, re-approve when needed

## Fix 1: Prune settings.local.json (HIGH IMPACT)

Replace granular entries with ~30 wildcard patterns. The wildcards cover all subcommands:

```json
{
  "permissions": {
    "allow": [
      "WebSearch",
      "WebFetch(domain:github.com)",
      "Bash(git:*)",
      "Bash(python3:*)",
      "Bash(.venv/bin/python3:*)",
      "Bash(/path/to/venv/python3:*)",
      "Bash(npm:*)",
      "Bash(npx:*)",
      "Bash(pip:*)",
      "Bash(docker:*)",
      "Bash(echo:*)",
      "Bash(cat:*)",
      "Bash(test:*)",
      "Bash(env:*)",
      "Bash(gh:*)"
    ]
  }
}
```

**Rule of thumb:** If the command prefix is a stable tool name, use `Bash(tool:*)`. Only add specific entries for tools where you want to restrict subcommands.

**Target:** < 50 entries. 30 is achievable for most projects.

## Fix 2: Harden Expensive PostToolUse Hooks

If a hook runs `grep -rl` or similar recursive scans on many files, two guards prevent stampedes:

**Guard 1: flock — prevent parallel execution**

Add at the top of the hook script (after shebang, before any logic):

```bash
LOCK_FILE="/tmp/my-hook-$(id -u).lock"
exec 200>"$LOCK_FILE"
flock -n 200 || exit 0   # -n = non-blocking; exit 0 if already locked
```

**Guard 2: separate cooldown for expensive operations**

If the hook has both cheap checks (frontmatter, regex) and expensive checks (`grep -rl` across thousands of files), give the expensive check its own longer cooldown:

```bash
LINKS_COOLDOWN_FILE="/tmp/my-hook-links-$(id -u).last"
run_links_check=true
if [[ -f "$LINKS_COOLDOWN_FILE" ]]; then
    links_last=$(cat "$LINKS_COOLDOWN_FILE" 2>/dev/null)
    links_now=$(date +%s)
    if [[ -n "$links_last" ]] && (( links_now - links_last < 300 )); then
        run_links_check=false
    fi
fi
if $run_links_check; then
    # expensive grep -rl here
    date +%s > "$LINKS_COOLDOWN_FILE"
fi
```

## Fix 3: Add Bloat Detection Hook (PREVENTION)

Create `.claude/hooks/permission-audit.sh`:

```bash
#!/usr/bin/env bash
COOLDOWN_FILE="/tmp/vault-perm-audit-$(id -u).last"
if [[ -f "$COOLDOWN_FILE" ]]; then
    last=$(cat "$COOLDOWN_FILE" 2>/dev/null)
    now=$(date +%s)
    [[ -n "$last" ]] && (( now - last < 86400 )) && exit 0
fi
date +%s > "$COOLDOWN_FILE"

SETTINGS="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)/.claude/settings.local.json"
[[ ! -f "$SETTINGS" ]] && exit 0

count=$(python3 -c "import json,sys; print(len(json.load(open('$SETTINGS')).get('permissions',{}).get('allow',[])))" 2>/dev/null)
[[ "$count" -gt 50 ]] && echo "VAULT_KEEPER: settings.local.json has ${count} permission entries (recommend < 50). Prune __NEW_LINE and shell fragment entries."
```

Register in `.claude/settings.json` under `UserPromptSubmit`:

```json
{
  "matcher": "",
  "hooks": [{ "type": "command", "command": "bash .claude/hooks/permission-audit.sh" }]
}
```

## Verification

```bash
# Entry count should be < 50
python3 -c "import json; print(len(json.load(open('.claude/settings.local.json'))['permissions']['allow']))"

# Valid JSON
python3 -m json.tool .claude/settings.local.json > /dev/null && echo "valid"

# Flock guard works (both should complete without error)
echo '{"tool_name":"Write","tool_input":{"file_path":"/path/file.md"}}' | bash .claude/hooks/your-hook.sh &
echo '{"tool_name":"Write","tool_input":{"file_path":"/path/file.md"}}' | bash .claude/hooks/your-hook.sh &
wait && echo "Both completed (second exited via flock)"

# Audit hook is silent with clean state
rm -f /tmp/vault-perm-audit-*.last
bash .claude/hooks/permission-audit.sh  # should produce no output
```

## Notes

- Session data is NOT lost when Claude Code crashes with stack overflow — restart and continue
- `__NEW_LINE_*` entries are harmless individually but compound: a single complex pipeline approval can add 10+ entries
- The permission matcher behavior is internal to Claude Code; the only lever is entry count reduction
- After pruning, re-approve commands as needed — Claude will prompt again; accept with the wildcard pattern to avoid re-bloat
