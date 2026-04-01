#!/usr/bin/env bash
# PostToolUse: Bash
# Detects common silent failure patterns in Bash output.
# Non-blocking: always exits 0.

INPUT=$(cat)

# Parse exit code and stderr from tool result
read -r EXIT_CODE STDERR <<< "$(echo "$INPUT" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    r = d.get('tool_result', d)
    ec = str(r.get('exit_code', r.get('exitCode', 0)) or 0)
    se = str(r.get('stderr', '') or '')
    # Collapse to single line for read
    print(ec, se.replace(chr(10), ' ')[:500])
except Exception:
    print('0 ')
" 2>/dev/null)" || exit 0

# Pattern: Exit 0 but stderr contains error keywords
if [ "$EXIT_CODE" = "0" ] && echo "$STDERR" | grep -qiE '(error|traceback|exception|fatal)' 2>/dev/null; then
    # Skip common false positives
    if echo "$STDERR" | grep -qiE '(deprecat|userwarning|futurewarning|ruff)' 2>/dev/null; then
        exit 0
    fi
    echo "[check-bash-output] Warning: Command exited 0 but stderr contains error indicators."
    echo "  Review stderr for silent failures before proceeding."
fi

exit 0
