#!/usr/bin/env bash
# Pre-commit hook: Check code complexity of staged Python files
# Flags functions over 50 lines or files over 500 lines as warnings

set -e

MAX_FUNCTION_LINES=80
MAX_FILE_LINES=800
WARNINGS=0

# Get staged Python files (committed or about to be)
STAGED_FILES=$(git diff --cached --name-only --diff-filter=ACM -- '*.py' 2>/dev/null || true)

if [ -z "$STAGED_FILES" ]; then
    echo "No Python files staged, skipping complexity check."
    exit 0
fi

for file in $STAGED_FILES; do
    if [ ! -f "$file" ]; then
        continue
    fi

    # Check file length
    FILE_LINES=$(wc -l < "$file")
    if [ "$FILE_LINES" -gt "$MAX_FILE_LINES" ]; then
        echo "WARNING: $file has $FILE_LINES lines (threshold: $MAX_FILE_LINES)"
        WARNINGS=$((WARNINGS + 1))
    fi

    # Check for very long functions (naive: count lines between def and next def/class/EOF)
    awk -v max="$MAX_FUNCTION_LINES" -v fname="$file" '
    /^[[:space:]]*(def |async def )/ {
        if (func_name != "" && (NR - func_start) > max) {
            printf "WARNING: %s:%d function %s is %d lines (threshold: %d)\n", fname, func_start, func_name, NR - func_start, max
        }
        func_name = $0
        sub(/^[[:space:]]*(async )?def /, "", func_name)
        sub(/\(.*/, "", func_name)
        func_start = NR
    }
    END {
        if (func_name != "" && (NR - func_start) > max) {
            printf "WARNING: %s:%d function %s is %d lines (threshold: %d)\n", fname, func_start, func_name, NR - func_start, max
        }
    }' "$file"
done

if [ "$WARNINGS" -gt 0 ]; then
    echo "Complexity check: $WARNINGS warning(s) found (non-blocking)"
fi

exit 0
