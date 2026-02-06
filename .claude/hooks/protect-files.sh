#!/bin/bash
# Block edits to protected files (credentials, lock files, generated artifacts).
# Exit 2 = block with reason on stderr.
INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

if [[ -z "$FILE_PATH" ]]; then
  exit 0
fi

case "$FILE_PATH" in
  *.env|*.env.*|*credentials*|*secrets*)
    echo "Blocked: refusing to modify secrets/credentials file" >&2
    exit 2
    ;;
  */uv.lock|*/package-lock.json|*/yarn.lock)
    echo "Blocked: lock files should be regenerated, not edited directly" >&2
    exit 2
    ;;
  */.git/*)
    echo "Blocked: never edit .git internals directly" >&2
    exit 2
    ;;
esac
exit 0
