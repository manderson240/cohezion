#!/usr/bin/env bash
# Pre-commit hook: Blocks commits when too many files are involved
# Prevents repeating the "8.6M files" or "1.45M files" incidents

set -e

MAX_FILE_COUNT=1000
MAX_INDEX_MB=50

# 1. Count untracked files
UNTRACKED_COUNT=$(git status --porcelain 2>/dev/null | grep -c "^??" || echo "0")

# 2. Count staged files
STAGED_COUNT=$(git diff --cached --name-only | wc -l)

# 3. Check Git index size
INDEX_SIZE_BYTES=$(stat -c %s .git/index 2>/dev/null || echo "0")
INDEX_SIZE_MB=$((INDEX_SIZE_BYTES / 1024 / 1024))

if [ "$UNTRACKED_COUNT" -gt "$MAX_FILE_COUNT" ]; then
    echo "❌ BLOCKED: $UNTRACKED_COUNT untracked files (max: $MAX_FILE_COUNT)"
    exit 1
fi

if [ "$STAGED_COUNT" -gt "$MAX_FILE_COUNT" ]; then
    echo "❌ BLOCKED: $STAGED_COUNT staged files (max: $MAX_FILE_COUNT)"
    echo "This looks like runaway generation. Use .gitignore to exclude these paths."
    exit 1
fi

if [ "$INDEX_SIZE_MB" -gt "$MAX_INDEX_MB" ]; then
    echo "❌ BLOCKED: Git index is too large ($INDEX_SIZE_MB MB, max: $MAX_INDEX_MB MB)"
    echo "Please remove runaway tracked files using 'git rm -r --cached <path>'."
    exit 1
fi

echo "✓ Git health OK ($UNTRACKED_COUNT untracked, $STAGED_COUNT staged, index ${INDEX_SIZE_MB}MB)"
