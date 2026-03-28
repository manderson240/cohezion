#!/usr/bin/env bash
# PreToolUse: Edit|Write
# Blocks edits on protected branches unless in an active worktree.
# Uses PreToolUse JSON protocol: {"decision": "block"} to prevent edits.

# Read stdin (hook JSON payload) to check file path
HOOK_INPUT=$(cat)

# Extract file_path from hook input (Edit or Write tool)
FILE_PATH=$(echo "$HOOK_INPUT" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(data.get('tool_input', {}).get('file_path', ''))
except Exception:
    print('')
" 2>/dev/null)

# If file is outside the git repo root, always allow
if [ -n "$FILE_PATH" ]; then
    REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null)
    if [ -n "$REPO_ROOT" ]; then
        # Resolve to absolute path for comparison
        ABS_FILE=$(python3 -c "import os; print(os.path.abspath('$FILE_PATH'))" 2>/dev/null)
        case "$ABS_FILE" in
            "$REPO_ROOT"/*) ;; # Inside repo, continue checks
            *) exit 0 ;;       # Outside repo, allow unconditionally
        esac
    fi
fi

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
