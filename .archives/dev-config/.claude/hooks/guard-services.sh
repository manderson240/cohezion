#!/usr/bin/env bash
# PreToolUse: Bash
# Warns when a command would stop or disable a critical Cohezion service.

INPUT=$(cat)

CMD=$(echo "$INPUT" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    print(d.get('tool_input', {}).get('command', ''))
except Exception:
    print('')
" 2>/dev/null)

[ -z "$CMD" ] && exit 0

# Critical services that should not be stopped without awareness
CRITICAL_SERVICES=(
    "cohezion-vault"
    "surrealdb"
    "tailscaled"
    "tailscale-funnel"
)

# Destructive systemctl actions
if echo "$CMD" | grep -qE 'systemctl\s+(stop|disable|mask|kill)\s'; then
    for svc in "${CRITICAL_SERVICES[@]}"; do
        if echo "$CMD" | grep -q "$svc"; then
            echo "[guard-services] Warning: about to stop/disable critical service '$svc'."
            echo "  The MCP vault and/or Tailscale Funnel may become unavailable."
            echo "  Proceed only if intentional."
            exit 0  # Warn but don't block — operator may have good reason
        fi
    done
fi

# pkill/kill targeting critical processes
if echo "$CMD" | grep -qE '(pkill|killall|kill)\s'; then
    for svc in surreal uvicorn tailscale; do
        if echo "$CMD" | grep -q "$svc"; then
            echo "[guard-services] Warning: killing process matching '$svc' may take down a critical service."
        fi
    done
fi

exit 0
