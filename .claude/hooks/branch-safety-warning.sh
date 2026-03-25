#!/usr/bin/env bash
# PreToolUse: Edit|Write
# Warns when editing files on main or develop branch.
# Non-blocking: exits 0 always, just prints a warning to stderr.

branch=$(git branch --show-current 2>/dev/null)
if [[ "$branch" == "main" || "$branch" == "develop" ]]; then
    echo "WARNING: You are on '$branch' branch. Consider switching to a feature branch." >&2
fi

exit 0
