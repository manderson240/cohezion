#!/usr/bin/env bash
# PreToolUse hook: Block writes to protected files that should not be
# modified without explicit review.
set -euo pipefail

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

if [[ -z "$FILE_PATH" ]]; then
  exit 0
fi

# Protected paths — these files affect governance and should not be
# modified casually during agentic sessions.
PROTECTED_PATTERNS=(
  ".agent/CONSTITUTION.md"
  ".agent/COHEZION_CHARTER.md"
  ".env"
  ".secrets.baseline"
)

for pattern in "${PROTECTED_PATTERNS[@]}"; do
  if [[ "$FILE_PATH" == *"$pattern"* ]]; then
    echo "Blocked: $FILE_PATH is a protected governance file. Modify manually if needed." >&2
    exit 2
  fi
done

exit 0
