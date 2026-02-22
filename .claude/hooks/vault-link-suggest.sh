#!/usr/bin/env bash
# vault-link-suggest.sh
# PostToolUse hook: surface link suggestions after Write/Edit to vault .md files.
#
# Exit 0 → stdout shown in Claude's transcript (suggestions visible)
# Exit 2 → stderr fed back as error (we never use this; always exit 0)
#
# JSON stdin structure: {"tool_name": "...", "tool_input": {"file_path": "..."}, ...}

set -euo pipefail

VAULT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PYTHON="/home/mike-anderson/dev/cohezion/cloud-vault-mcp/.venv/bin/python3"
LOG_FILE="/tmp/vault-link-suggest.log"
COOLDOWN_FILE="/tmp/vault-link-suggest.last"
COOLDOWN_SECONDS=30

# ── Read stdin ────────────────────────────────────────────────────────────────
input=$(cat)

# ── Extract file_path from tool_input ────────────────────────────────────────
file_path=$(echo "$input" | jq -r '.tool_input.file_path // empty' 2>/dev/null || true)

# Exit silently if no file_path or jq failed
if [[ -z "$file_path" ]]; then
    exit 0
fi

# ── Filter: only vault .md files ─────────────────────────────────────────────
# Must end in .md
if [[ "$file_path" != *.md ]]; then
    exit 0
fi

# ── Cooldown: skip if run recently ───────────────────────────────────────────
if [[ -f "$COOLDOWN_FILE" ]]; then
    last=$(cat "$COOLDOWN_FILE" 2>/dev/null || echo 0)
    now=$(date +%s)
    elapsed=$(( now - last ))
    if (( elapsed < COOLDOWN_SECONDS )); then
        exit 0
    fi
fi

# Update cooldown timestamp
date +%s > "$COOLDOWN_FILE" 2>/dev/null || true

# ── Run vault_linker suggest ──────────────────────────────────────────────────
PYTHONPATH="$VAULT_ROOT/tools" "$PYTHON" -m vault_linker suggest \
    "$file_path" \
    --vault-path "$VAULT_ROOT" \
    2>>"$LOG_FILE" || true

exit 0
