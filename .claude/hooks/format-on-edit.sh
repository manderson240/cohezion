#!/usr/bin/env bash
# PostToolUse: Edit|Write
# Runs ruff format on Python files after they're edited.
# Non-blocking: always exits 0, only formats .py files.

INPUT=$(cat)

FILE=$(echo "$INPUT" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    print(d.get('tool_input', {}).get('file_path', ''))
except Exception:
    print('')
" 2>/dev/null)

[ -z "$FILE" ] && exit 0

# Only format Python files
[[ "$FILE" != *.py ]] && exit 0

# Only format files that exist
[ -f "$FILE" ] || exit 0

# Run ruff format quietly — don't spam output on every edit
if command -v ruff &>/dev/null; then
    ruff format --quiet "$FILE" 2>/dev/null
elif command -v uv &>/dev/null; then
    uv run ruff format --quiet "$FILE" 2>/dev/null
fi

exit 0
