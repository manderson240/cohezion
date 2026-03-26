#!/usr/bin/env bash
# SessionStart: Branch & worktree isolation status
# Prints context for Claude about current branch and isolation state.
# Non-blocking: exits 0 always.

PROTECTED_PATTERNS=("main" "develop" "challenge/*" "release/*")

branch=$(git branch --show-current 2>/dev/null || echo "DETACHED")
worktree_json=$(cz worktree status --json 2>/dev/null || echo '{"active": false}')
worktree_active=$(echo "$worktree_json" | python3 -c "import sys,json; print(json.load(sys.stdin).get('active', False))" 2>/dev/null)

# Check if branch matches any protected pattern
is_protected=false
for pattern in "${PROTECTED_PATTERNS[@]}"; do
    case "$branch" in
        $pattern) is_protected=true; break ;;
    esac
done

echo "[session-isolation] Branch: $branch | Worktree active: $worktree_active"

if [ "$is_protected" = true ] && [ "$worktree_active" != "True" ]; then
    echo "[session-isolation] ISOLATION RECOMMENDED: '$branch' is a shared/protected branch."
    echo "[session-isolation] Before editing, create a worktree: cz worktree create --json <slug>"
    echo "[session-isolation] Protected patterns: ${PROTECTED_PATTERNS[*]}"
fi

exit 0
