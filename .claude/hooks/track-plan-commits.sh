#!/usr/bin/env bash
# PostToolUse: Bash
# Records git commits in SurrealDB for plan traceability.
# Non-blocking: always exits 0. SurrealDB failures are silent.

INPUT=$(cat)

# Extract command from tool_input
COMMAND=$(echo "$INPUT" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    print(d.get('tool_input', {}).get('command', ''))
except Exception:
    print('')
" 2>/dev/null) || true

[ -z "$COMMAND" ] && exit 0

# Only act on git commit commands
case "$COMMAND" in
    *git\ commit*|*git\ -c*commit*) ;;
    *) exit 0 ;;
esac

# Try to extract commit hash from tool_response stdout, fall back to git log
COMMIT_HASH=$(echo "$INPUT" | python3 -c "
import sys, json, re
try:
    d = json.load(sys.stdin)
    stdout = d.get('tool_response', {}).get('stdout', '')
    if not stdout:
        stdout = str(d.get('tool_result', ''))
    # Look for a 40-char hex hash in the output
    m = re.search(r'[0-9a-f]{40}', stdout)
    if m:
        print(m.group(0))
    else:
        # Look for short hash in typical git commit output like '[branch abc1234] message'
        m = re.search(r'\[[\w/.-]+\s+([0-9a-f]{7,})\]', stdout)
        if m:
            print(m.group(1))
        else:
            print('')
except Exception:
    print('')
" 2>/dev/null) || true

# Fall back to git log if we couldn't parse it from output
if [ -z "$COMMIT_HASH" ]; then
    COMMIT_HASH=$(git log -1 --format=%H 2>/dev/null) || true
fi

[ -z "$COMMIT_HASH" ] && exit 0

# Record commit in SurrealDB (fail silently)
uv run python -c "
from cohezion.traceability.plan_graph import PlanGraph
import asyncio
asyncio.run(PlanGraph().record_commit_if_active('$COMMIT_HASH'))
" 2>/dev/null || true

exit 0
