#!/usr/bin/env bash
# PostToolUse hook: suggest vault links after Write/Edit to .md files.
#
# Called with tool input JSON on stdin. Exits 0 in all cases to avoid
# blocking Claude Code. Errors are logged to /tmp/vault-link-suggest.log.
#
# Cooldown: silently exits if last run was <30 seconds ago.

VAULT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
COOLDOWN_FILE="/tmp/vault-link-suggest.last"
ERROR_LOG="/tmp/vault-link-suggest.log"
COOLDOWN_SECONDS=30

# ── Extract file_path from stdin JSON ────────────────────────────────────────
stdin_json=$(cat)

if ! command -v jq >/dev/null 2>&1; then
    echo "vault-link-suggest: jq not found, skipping" >> "$ERROR_LOG"
    exit 0
fi

file_path=$(echo "$stdin_json" | jq -r '.tool_input.file_path // empty' 2>/dev/null)

# Silently exit for missing/null file_path or non-.md files
[[ -z "$file_path" ]] && exit 0
[[ "$file_path" != *.md ]] && exit 0

# ── Cooldown check ────────────────────────────────────────────────────────────
if [[ -f "$COOLDOWN_FILE" ]]; then
    last_run=$(cat "$COOLDOWN_FILE" 2>/dev/null)
    now=$(date +%s)
    if [[ -n "$last_run" ]] && (( now - last_run < COOLDOWN_SECONDS )); then
        exit 0
    fi
fi

# Update cooldown timestamp
date +%s > "$COOLDOWN_FILE"

# ── Run vault_linker suggest ──────────────────────────────────────────────────
export PYTHONPATH="$VAULT_ROOT/tools"

python3 -m vault_linker suggest "$file_path" --vault-path "$VAULT_ROOT" 2>>"$ERROR_LOG"

# Always exit 0 — never block Claude Code on vault_linker failures
exit 0
