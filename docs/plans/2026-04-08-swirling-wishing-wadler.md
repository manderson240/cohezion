# Fix SessionStart Hook Error

## Context

Every session start shows "SessionStart:startup hook error" because the `entire hooks claude-code session-start` command in `.claude/settings.json` (project-level) fails with exit code 1. Entire v0.5.3 requires `session_id` in the stdin JSON, but Claude Code's SessionStart hook doesn't provide it.

## Root Cause

- File: `/home/mike-anderson/dev/cohezion/.claude/settings.json` line 9
- Command: `entire hooks claude-code session-start`
- Error: `"no session_id in SessionStart event"` (exit 1)
- Entire expects `{"session_id": "..."}` on stdin; Claude Code passes empty or no-session-id JSON

## Fix

### Step 1: Create wrapper script

Create `.claude/hooks/entire-session-start.sh` that:
1. Reads stdin from Claude Code (preserves any other fields)
2. Injects `session_id` if missing — uses the Claude Code session JSONL path to derive the ID, falling back to a generated UUID
3. Pipes augmented JSON to `entire hooks claude-code session-start`
4. Exits 0 regardless (entire's SessionStart response is informational, not critical)

Uses `jq` (confirmed available: jq-1.7) for JSON manipulation.

### Step 2: Update project settings

Modify `.claude/settings.json` line 9 to use the wrapper:
```diff
- "command": "entire hooks claude-code session-start"
+ "command": ".claude/hooks/entire-session-start.sh"
```

## Files to Modify

| File | Action |
|------|--------|
| `.claude/hooks/entire-session-start.sh` | **Create** — wrapper script |
| `.claude/settings.json` | **Edit** line 9 — point to wrapper |

## Verification

1. Run the wrapper manually: `echo '{}' | .claude/hooks/entire-session-start.sh` — should exit 0
2. Start a new Claude Code session in the cohezion project — no "startup hook error"
3. Check `.entire/logs/entire.log` — should show a `session-start` entry with a valid session_id
