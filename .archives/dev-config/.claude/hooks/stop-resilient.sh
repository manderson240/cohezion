#!/bin/bash
# Resilient Stop hook: wraps `entire hooks claude-code stop` so that subprocess
# sessions (e.g. `claude -p --no-session-persistence`) don't leak zombie
# entries into `entire sessions list`.
#
# Behavior:
#   1. Read hook input JSON from stdin (Claude Code passes session_id, transcript_path, etc.)
#   2. If transcript_path exists → invoke `entire hooks claude-code stop` normally
#   3. Else → fall back to `entire sessions stop <session_id> --force` which
#      fires the state-machine SessionStop event without trying to read a transcript
#   4. Always exit 0 so the hook chain never blocks session shutdown
#
# Installed at: .claude/hooks/stop-resilient.sh
# Wired from  : .claude/settings.json → hooks.Stop
#
# Discovery   : 2026-04-18 session — 10 stale sessions accumulated over 6 days
# Root cause  : `claude -p` print-mode doesn't persist transcript, so
#               `entire hooks claude-code stop` errored with "transcript file not
#               found" but exit-0, and the session stayed in `active` state forever.

set -u

# Capture stdin (hook input JSON)
INPUT="$(cat)"

# Extract session_id and transcript_path with jq if available, else python3
SESSION_ID=""
TRANSCRIPT_PATH=""
if command -v jq >/dev/null 2>&1; then
    SESSION_ID="$(echo "$INPUT" | jq -r '.session_id // ""' 2>/dev/null)"
    TRANSCRIPT_PATH="$(echo "$INPUT" | jq -r '.transcript_path // ""' 2>/dev/null)"
elif command -v python3 >/dev/null 2>&1; then
    SESSION_ID="$(echo "$INPUT" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("session_id",""))' 2>/dev/null || echo "")"
    TRANSCRIPT_PATH="$(echo "$INPUT" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("transcript_path",""))' 2>/dev/null || echo "")"
fi

# Primary path: transcript exists → let entire do its full stop-hook dance
if [ -n "$TRANSCRIPT_PATH" ] && [ -f "$TRANSCRIPT_PATH" ]; then
    echo "$INPUT" | entire hooks claude-code stop 2>&1 | head -20
    exit 0
fi

# Fallback path: transcript missing (likely a `claude -p` subprocess, a
# crashed session, or a non-persistent invocation). Fire the state-machine
# SessionStop event directly so the session doesn't stay "active" forever.
#
# SECURITY: validate SESSION_ID format before passing to an external binary.
# UUIDs are [0-9a-f-], nothing else. Prevents metacharacter injection into
# a downstream tool that may shell-interpret its arguments (defense-in-depth).
if [ -n "$SESSION_ID" ]; then
    if [[ "$SESSION_ID" =~ ^[a-zA-Z0-9_-]+$ ]]; then
        entire sessions stop "$SESSION_ID" --force 2>&1 | head -5
    else
        echo "stop-resilient: refusing session_id with unexpected chars: $SESSION_ID" >&2
    fi
fi

exit 0
