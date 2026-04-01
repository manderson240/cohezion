#!/usr/bin/env bash
# PostToolUse: Edit|Write
# Runs the nearest test file when a src/cohezion/ Python file is edited.
# Non-blocking: always exits 0. Only prints warnings on regression.

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
[[ "$FILE" != *.py ]] && exit 0
[[ "$FILE" != */src/cohezion/* ]] && exit 0
[ -f "$FILE" ] || exit 0

# Derive test file path: src/cohezion/foo/bar.py -> tests/foo/test_bar.py
REL="${FILE#*src/cohezion/}"
DIR=$(dirname "$REL")
BASE=$(basename "$REL" .py)
ROOT=$(git -C "$(dirname "$FILE")" rev-parse --show-toplevel 2>/dev/null) || exit 0
TEST_FILE="${ROOT}/tests/${DIR}/test_${BASE}.py"

if [ -f "$TEST_FILE" ]; then
    OUTPUT=$(cd "$ROOT" && timeout 30 uv run pytest "$TEST_FILE" -q --tb=line 2>&1 | tail -5) || true
    if echo "$OUTPUT" | grep -q "failed"; then
        echo "[test-on-edit] REGRESSION detected in $TEST_FILE:"
        echo "$OUTPUT"
    fi
fi

exit 0
