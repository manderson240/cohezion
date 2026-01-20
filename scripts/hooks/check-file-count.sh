#!/usr/bin/env bash
# Pre-commit hook: Blocks commits when too many untracked files exist
# Prevents repeating the "1.45M files" incident

set -e

MAX_UNTRACKED=5000
UNTRACKED_COUNT=$(git status --porcelain 2>/dev/null | grep -c "^??" || echo "0")

if [ "$UNTRACKED_COUNT" -gt "$MAX_UNTRACKED" ]; then
    echo "❌ BLOCKED: $UNTRACKED_COUNT untracked files (max: $MAX_UNTRACKED)"
    echo ""
    echo "This usually means generated files aren't in .gitignore."
    echo "Run: git status --porcelain | grep '^??' | head -20"
    echo "Then add appropriate patterns to .gitignore"
    exit 1
fi

echo "✓ File count OK ($UNTRACKED_COUNT untracked)"
