#!/bin/bash
# HOOK_NAME: format-on-edit
# HOOK_STAGE: post_operation
# HOOK_ACTION: allow
# HOOK_TIMEOUT: 10
# HOOK_DESCRIPTION: Auto-format Python files after Claude edits/writes them
# Receives tool input JSON on stdin. Extracts file_path and runs ruff.
INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

# Only format Python files that exist
if [[ -n "$FILE_PATH" && "$FILE_PATH" == *.py && -f "$FILE_PATH" ]]; then
  ruff format --quiet "$FILE_PATH" 2>/dev/null
  ruff check --quiet --fix "$FILE_PATH" 2>/dev/null
fi
exit 0
