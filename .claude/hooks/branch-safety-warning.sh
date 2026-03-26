#!/usr/bin/env bash
# PreToolUse: Edit|Write
# Blocks edits on protected branches unless in an active worktree.
# Uses PreToolUse JSON protocol: {"decision": "block"} to prevent edits.

PROTECTED_PATTERNS=("main" "develop" "challenge/*" "release/*")

branch=$(git branch --show-current 2>/dev/null || echo "")
worktree_active=$(cz worktree status --json 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin).get('active', False))" 2>/dev/null)

# If in an active worktree, always allow (worktree IS the isolation)
if [ "$worktree_active" = "True" ]; then
    exit 0
fi

# Check if branch matches any protected pattern
is_protected=false
for pattern in "${PROTECTED_PATTERNS[@]}"; do
    case "$branch" in
        $pattern) is_protected=true; break ;;
    esac
done

if [ "$is_protected" = true ]; then
    echo '{"decision":"block","reason":"BLOCKED: Editing on protected branch '"'$branch'"'. Create a worktree first: cz worktree create --json <slug>"}'
    exit 0
fi

exit 0
