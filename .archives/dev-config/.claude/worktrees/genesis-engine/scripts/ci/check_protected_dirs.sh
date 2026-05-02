#!/usr/bin/env bash
# Protected Directory Check
#
# Prevents accidental deletion of critical directories during automated
# operations (CI, cleanup scripts, ShadowScripter, etc.).
#
# Usage:
#   As a pre-commit hook or CI step:
#     ./scripts/ci/check_protected_dirs.sh
#
#   Returns exit code 1 if protected directories are being deleted.

set -euo pipefail

# Directories that must never be bulk-deleted
PROTECTED_DIRS=(
    "_bmad/"
    ".claude/commands/"
    ".claude/hooks/"
    ".agent/"
    ".github/workflows/"
    "src/cohezion/"
    "scripts/ci/"
    "scripts/dba/"
    "scripts/security/"
)

# Check staged deletions
deleted_files=$(git diff --cached --diff-filter=D --name-only 2>/dev/null || true)
if [[ -z "$deleted_files" ]]; then
    exit 0
fi

errors=0

for protected in "${PROTECTED_DIRS[@]}"; do
    # Count how many files in this protected dir are being deleted
    delete_count=$(echo "$deleted_files" | grep -c "^${protected}" 2>/dev/null || true)
    total_count=$(git ls-files -- "${protected}" 2>/dev/null | wc -l || echo 0)

    if [[ "$delete_count" -gt 0 && "$total_count" -gt 0 ]]; then
        # Allow deleting a few files (normal refactoring), block bulk deletion
        threshold=$(( total_count / 2 ))
        if [[ "$threshold" -lt 5 ]]; then
            threshold=5
        fi

        if [[ "$delete_count" -ge "$threshold" ]]; then
            echo "ERROR: Bulk deletion detected in protected directory: $protected"
            echo "  Deleting $delete_count of $total_count files (threshold: $threshold)"
            echo "  If intentional, use: git commit --no-verify"
            errors=$((errors + 1))
        fi
    fi
done

if [[ "$errors" -gt 0 ]]; then
    echo ""
    echo "Protected directory check FAILED. $errors violation(s) found."
    echo "This prevents accidental deletion by automated tools."
    exit 1
fi
