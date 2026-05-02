#!/usr/bin/env bash
# PreToolUse: Write
# Warns when creating NEW files in src/ (possible infrastructure drift).
# Non-blocking: always exits 0.

INPUT=$(cat)

FILE=$(echo "$INPUT" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    print(d.get('tool_input', {}).get('file_path', ''))
except Exception:
    print('')
" 2>/dev/null) || true

[ -z "$FILE" ] && exit 0

# Only care about new files in src/
[[ "$FILE" != */src/* ]] && exit 0

# If file already exists, this is a modification, not drift
[ -f "$FILE" ] && exit 0

echo "[drift-detection] Creating NEW file in src/: $(basename "$FILE")"
echo "  Is this file directly required by the current task?"
echo "  If building infrastructure/framework code, review Scope Boundaries in workflow-enforcement.md."

exit 0
