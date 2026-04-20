#!/usr/bin/env bash
# PostToolUse: Edit|Write
# Runs ruff check on edited Python files. Non-blocking.

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
[[ "$FILE" != *.py ]] && exit 0
[ -f "$FILE" ] || exit 0

# Run ruff check — errors and warnings only (style handled by format-on-edit)
if command -v ruff &>/dev/null; then
    OUTPUT=$(ruff check --select E,F,W "$FILE" 2>/dev/null)
elif command -v uv &>/dev/null; then
    OUTPUT=$(uv run ruff check --select E,F,W "$FILE" 2>/dev/null)
fi

if [ -n "$OUTPUT" ]; then
    echo "[lint-on-edit] Issues found:"
    echo "$OUTPUT"
fi

exit 0
