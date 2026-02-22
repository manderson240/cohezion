#!/usr/bin/env bash
# PreToolUse hook: Block dangerous bash commands that could corrupt the repo
# or leak secrets.
set -euo pipefail

INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty')

if [[ -z "$COMMAND" ]]; then
  exit 0
fi

# Extract the base command (first word) to avoid false positives on
# arguments. E.g. `gh pr create --body "...pip install..."` should not
# trigger the pip guard.
BASE_CMD=$(echo "$COMMAND" | head -1 | awk '{print $1}')

# Block bare pip/pip3 as the primary command
if [[ "$BASE_CMD" == "pip" ]] || [[ "$BASE_CMD" == "pip3" ]]; then
  echo "Blocked: use 'uv pip' instead of bare '$BASE_CMD'." >&2
  exit 2
fi

# Block dangerous patterns in the actual command
BLOCKED_PATTERNS=(
  "git push.*--force"  # No force push
  "git push.*-f "      # No force push
  "git reset --hard"   # No hard reset
  "rm -rf /"           # No root delete
  "rm -rf ~"           # No home delete
  "> /dev/sd"          # No disk writes
  "mkfs"               # No filesystem creation
  "dd if="             # No raw disk operations
)

for pattern in "${BLOCKED_PATTERNS[@]}"; do
  if echo "$COMMAND" | grep -qF "$pattern"; then
    echo "Blocked: command matches dangerous pattern '$pattern'. Use safe alternatives." >&2
    exit 2
  fi
done

exit 0
