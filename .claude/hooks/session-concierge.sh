#!/usr/bin/env bash
# SessionStart hook: Gather session state for the concierge briefing.
# This runs on every session start and outputs a concise state summary
# that the main agent can use to avoid cold starts.

set -euo pipefail

echo "{"
echo '  "type": "session_briefing",'

# 1. Current branch
BRANCH=$(git branch --show-current 2>/dev/null || echo "detached")
echo "  \"branch\": \"$BRANCH\","

# 2. Active worktrees
WT_COUNT=$(git worktree list 2>/dev/null | wc -l)
echo "  \"worktrees\": $WT_COUNT,"

# 3. Most recent continuation file
LATEST_CONT=$(find ~/.cohezion-engine/sessions/ -name "continuation.md" -mtime -3 2>/dev/null | sort -r | head -1)
if [ -n "$LATEST_CONT" ]; then
    CONT_TASK=$(grep "^\\*\\*Task:\\*\\*" "$LATEST_CONT" 2>/dev/null | head -1 | sed 's/\*\*Task:\*\* //')
    echo "  \"continuation\": \"$CONT_TASK\","
else
    echo '  "continuation": null,'
fi

# 4. Active plans count
PLAN_COUNT=$(ls docs/plans/*.md ~/.claude/plans/*.md 2>/dev/null | wc -l)
echo "  \"plans\": $PLAN_COUNT,"

# 5. SurrealDB status (quick check)
SURREAL_OK=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8001/health 2>/dev/null || echo "000")
echo "  \"surrealdb\": \"$SURREAL_OK\","

# 6. Recent vault entries
VAULT_RECENT=$(find ~/vaults/cohezion-vault/cerebellum/ -name "*.md" -mtime -3 2>/dev/null | wc -l)
echo "  \"vault_recent_entries\": $VAULT_RECENT,"

# 7. Last 3 commits
LAST_COMMITS=$(git log --oneline -3 2>/dev/null | tr '\n' '|' | sed 's/|$//')
echo "  \"recent_commits\": \"$LAST_COMMITS\""

echo "}"
