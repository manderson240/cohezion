#!/usr/bin/env bash
# PostToolUse: Edit|Write
# Records file touches in SurrealDB for plan traceability.
# Non-blocking: always exits 0. SurrealDB failures are silent.

INPUT=$(cat)

FILE_PATH=$(echo "$INPUT" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    # Try tool_input first (Edit/Write), fall back to tool_response
    fp = d.get('tool_input', {}).get('file_path', '')
    if not fp:
        fp = d.get('tool_response', {}).get('file_path', '')
    print(fp)
except Exception:
    print('')
" 2>/dev/null) || true

[ -z "$FILE_PATH" ] && exit 0

# Skip internal/generated directories
case "$FILE_PATH" in
    */.claude/*|*/node_modules/*|*/.venv/*|*/__pycache__/*|*/.git/*) exit 0 ;;
esac

# Record file touch in SurrealDB (fail silently)
uv run python -c "
from cohezion.traceability.plan_graph import PlanGraph
import asyncio
asyncio.run(PlanGraph().record_file_touch_if_active('$FILE_PATH'))
" 2>/dev/null || true

exit 0
