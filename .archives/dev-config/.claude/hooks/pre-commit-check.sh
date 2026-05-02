#!/usr/bin/env bash
# PreToolUse: Bash
# Runs quick quality check before git commit commands.

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

# Quick lint check (errors only, fast)
LINT_OUTPUT=$(ruff check --select E,F src/cohezion/ 2>/dev/null | head -5)
if [ -n "$LINT_OUTPUT" ]; then
    echo "[pre-commit-check] Lint errors detected — fix before committing:"
    echo "$LINT_OUTPUT"
    echo "  Run: ruff check --select E,F src/cohezion/"
    exit 2  # Block the commit
fi

exit 0
