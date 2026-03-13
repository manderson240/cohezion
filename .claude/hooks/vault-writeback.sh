#!/usr/bin/env bash
# PostToolUse hook: Write-back edited vault notes to SurrealDB in real-time.
#
# Fires on Write|Edit. Extracts file_path, checks it's a vault .md note,
# then calls vault_sync.py sync to update the neuron immediately.
#
# Silent on all errors — never blocks Claude Code.

VAULT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SCRIPT="${VAULT_ROOT}/scripts/vault_sync.py"

# ── Extract file_path from stdin JSON ────────────────────────────────────────
stdin_json=$(cat)

if ! command -v jq >/dev/null 2>&1; then
    exit 0
fi

file_path=$(echo "$stdin_json" | jq -r '.tool_input.file_path // empty' 2>/dev/null)

# Only process vault .md files
[[ -z "$file_path" ]]        && exit 0
[[ "$file_path" != *.md ]]   && exit 0
[[ "$file_path" != "${VAULT_ROOT}"* ]] && exit 0

# Skip tooling and meta directories
[[ "$file_path" == *"/obsidian-plugin/"* ]] && exit 0
[[ "$file_path" == *"/mcp-server/"* ]]      && exit 0
[[ "$file_path" == *"/tools/"* ]]           && exit 0
[[ "$file_path" == *"/.claude/"* ]]         && exit 0
[[ "$file_path" == *"/scripts/"* ]]         && exit 0
[[ "$file_path" == *"/docs/"* ]]            && exit 0

# ── Sync to SurrealDB (skip if another sync is in-flight) ─────────────────────
LOCK_FILE="/tmp/vault-writeback-$(id -u).lock"
if ! mkdir "$LOCK_FILE" 2>/dev/null; then
    exit 0
fi

(
    python3 "$SCRIPT" sync "$file_path" >/dev/null 2>&1
    rmdir "$LOCK_FILE" 2>/dev/null
) &

exit 0
