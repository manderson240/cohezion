#!/bin/bash
# PreToolUse hook for Bash: warns about sensitive commands that should NOT be "Allow always".
# Outputs warning to stdout (shown in permission prompt), exits 0 to let it proceed.
# Only fires for commands that aren't auto-allowed (i.e. ones that trigger a prompt).

COMMAND=$(cat | jq -r '.tool_input.command // empty')

if [[ -z "$COMMAND" ]]; then
  exit 0
fi

# Patterns that are NOT in the auto-allow list and should never be "Allow always"
WARN=0
case "$COMMAND" in
  git\ push*|git\ reset*|git\ checkout*|git\ merge*|git\ rebase*)
    WARN=1 ;;
  git\ config*|git\ credential*)
    WARN=1 ;;
  docker*|docker-compose*)
    WARN=1 ;;
  sudo\ *)
    WARN=1 ;;
  curl\ *|wget\ *)
    WARN=1 ;;
  npm\ *|npx\ *|node\ *)
    WARN=1 ;;
  chmod\ *|xargs\ *|rm\ *)
    WARN=1 ;;
esac

if [[ "$WARN" -eq 1 ]]; then
  echo "SENSITIVE COMMAND — if prompted, approve with \"Allow once\", not \"Allow always\""
fi

exit 0
