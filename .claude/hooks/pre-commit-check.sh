#!/usr/bin/env bash
# PreToolUse: Bash
# Runs quick quality check before git commit commands.
# Phase 1: Lint check (ruff E,F errors)
# Phase 2: Targeted tests for changed modules (30s timeout)

INPUT=$(cat)

CMD=$(echo "$INPUT" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    print(d.get('tool_input', {}).get('command', ''))
except Exception:
    print('')
" 2>/dev/null)

[ -z "$CMD" ] && exit 0

# Only trigger on git commit commands
echo "$CMD" | grep -qE '^\s*git\s+commit' || exit 0

# Phase 1: Quick lint check (errors only, fast)
LINT_OUTPUT=$(ruff check --select E,F src/cohezion/ 2>/dev/null | head -5)
if [ -n "$LINT_OUTPUT" ]; then
    echo "[pre-commit-check] Lint errors detected — fix before committing:"
    echo "$LINT_OUTPUT"
    echo "  Run: ruff check --select E,F src/cohezion/"
    exit 2  # Block the commit
fi

# Phase 2: Targeted tests for changed modules
# Detect which src/cohezion/ modules have staged changes
CHANGED_MODULES=$(git diff --cached --name-only -- 'src/cohezion/' 2>/dev/null \
    | sed -n 's|^src/cohezion/\([^/]*\)/.*|\1|p' \
    | sort -u)

if [ -z "$CHANGED_MODULES" ]; then
    exit 0  # No cohezion source changes staged
fi

TESTED=0
FAILED=0
for MODULE in $CHANGED_MODULES; do
    TEST_DIR="tests/${MODULE}"
    [ -d "$TEST_DIR" ] || continue

    TESTED=$((TESTED + 1))
    # Run with 30s timeout, fail-fast, minimal output
    RESULT=$(timeout 30 uv run pytest "$TEST_DIR" -q --tb=no -x 2>&1 | tail -1)
    if echo "$RESULT" | grep -qE 'failed|error'; then
        echo "[pre-commit-check] Tests failing in $TEST_DIR:"
        echo "  $RESULT"
        FAILED=$((FAILED + 1))
    fi
done

if [ "$FAILED" -gt 0 ]; then
    echo "[pre-commit-check] $FAILED/$TESTED module test suites have failures — fix before committing."
    exit 2  # Block the commit
fi

if [ "$TESTED" -gt 0 ]; then
    echo "[pre-commit-check] $TESTED module test suite(s) passed."
fi

exit 0
