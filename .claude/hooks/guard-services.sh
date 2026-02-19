#!/usr/bin/env bash
# guard-services.sh - PreToolUse[Bash] hook for Claude Code
#
# Prevents AI coding tools from accidentally creating runaway services
# or infinite loops that could crash the system.
#
# How it works:
#   - Claude Code pipes JSON with the command to stdin
#   - Exit 0 = allow the command
#   - Exit 2 = block the command (message printed to stderr)
#
# Cross-tool adaptation:
#   - Antigravity: Copy to .antigravity/hooks/ and register in config
#   - Gemini CLI: Register as a pre-execution hook in .gemini/config.json
#   - OpenCode: Register as a command interceptor in settings

set -euo pipefail

# Read the tool input from stdin
INPUT=$(cat)

# Extract the command field from JSON
COMMAND=$(echo "$INPUT" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(data.get('command', ''))
except:
    print('')
" 2>/dev/null || echo "")

# If we can't parse the command, allow it (don't block on parse errors)
if [[ -z "$COMMAND" ]]; then
    exit 0
fi

# --- BLOCK: Service files with Restart=always but no StartLimitBurst ---
# This is the exact pattern that caused the 129K restart crash loop
if echo "$COMMAND" | grep -qiE '(cat|tee|write|echo).*\.service' 2>/dev/null; then
    if echo "$COMMAND" | grep -qi 'Restart=always' 2>/dev/null; then
        if ! echo "$COMMAND" | grep -qi 'StartLimitBurst' 2>/dev/null; then
            echo "BLOCKED: Service file contains Restart=always without StartLimitBurst." >&2
            echo "This can cause infinite crash loops. Add StartLimitBurst=N and" >&2
            echo "StartLimitIntervalSec=N in the [Unit] section." >&2
            exit 2
        fi
    fi
fi

# --- WARN: Infinite loop patterns without timeout ---
if echo "$COMMAND" | grep -qE '(while\s+true|while\s+:|\bfor\s*\(\s*;\s*;\s*\))' 2>/dev/null; then
    if ! echo "$COMMAND" | grep -qiE '(timeout|sleep\s+[0-9]|break|exit)' 2>/dev/null; then
        echo "WARNING: Detected infinite loop pattern without timeout/break." >&2
        echo "Consider wrapping with 'timeout N' or adding a break condition." >&2
        # Warn only, don't block (exit 0)
    fi
fi

# --- WARN: Backgrounding processes that could outlive the session ---
if echo "$COMMAND" | grep -qE '(nohup\s|&\s*$|disown)' 2>/dev/null; then
    if ! echo "$COMMAND" | grep -qiE '(timeout|kill|trap)' 2>/dev/null; then
        echo "WARNING: Backgrounding a process without cleanup mechanism." >&2
        echo "Use 'timeout N command &' or set up a trap for cleanup." >&2
        # Warn only, don't block (exit 0)
    fi
fi

# --- BLOCK: systemctl mask/unmask without explicit service name ---
if echo "$COMMAND" | grep -qE 'systemctl\s+(mask|unmask)\s*$' 2>/dev/null; then
    echo "BLOCKED: systemctl mask/unmask requires an explicit service name." >&2
    exit 2
fi

# Allow the command
exit 0
