#!/usr/bin/env bash
# PostToolUse hook: Auto-lint Python files after Edit/Write operations.
# Runs ruff format + check on the modified file for immediate feedback.
set -euo pipefail

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

# Only act on Python files
if [[ -z "$FILE_PATH" ]] || [[ "$FILE_PATH" != *.py ]]; then
  exit 0
fi

# Only act if file exists (Write may have created it)
if [[ ! -f "$FILE_PATH" ]]; then
  exit 0
fi

# Run ruff format (auto-fix) then check (report issues)
cd "${CLAUDE_PROJECT_DIR:-.}"
uv run ruff format "$FILE_PATH" 2>/dev/null || true
LINT_OUTPUT=$(uv run ruff check "$FILE_PATH" 2>/dev/null || true)

if [[ -n "$LINT_OUTPUT" ]]; then
  echo "Ruff found issues in $FILE_PATH:"
  echo "$LINT_OUTPUT"
fi

exit 0
