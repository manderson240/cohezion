#!/usr/bin/env bash
# UserPromptSubmit hook: Warn when settings.local.json permission entries exceed threshold.
# Prevents gradual bloat from auto-approved multi-line bash commands.
# Cooldown: once per day (86400s).

COOLDOWN_FILE="/tmp/vault-perm-audit-$(id -u).last"
COOLDOWN_SECONDS=86400

if [[ -f "$COOLDOWN_FILE" ]]; then
    last_run=$(cat "$COOLDOWN_FILE" 2>/dev/null)
    now=$(date +%s)
    if [[ -n "$last_run" ]] && (( now - last_run < COOLDOWN_SECONDS )); then
        exit 0
    fi
fi

date +%s > "$COOLDOWN_FILE"

SETTINGS_FILE="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)/.claude/settings.local.json"

if [[ ! -f "$SETTINGS_FILE" ]]; then
    exit 0
fi

if ! command -v python3 >/dev/null 2>&1; then
    exit 0
fi

count=$(python3 -c "
import json, sys
try:
    data = json.load(open('$SETTINGS_FILE'))
    print(len(data.get('permissions', {}).get('allow', [])))
except Exception:
    print(0)
" 2>/dev/null)

if [[ "$count" -gt 50 ]]; then
    echo "VAULT_KEEPER: settings.local.json has ${count} permission entries (recommend < 50). Prune __NEW_LINE and shell fragment entries."
fi

exit 0
