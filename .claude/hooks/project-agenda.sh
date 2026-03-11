#!/usr/bin/env bash
# UserPromptSubmit hook: Surface active project P0 tasks at session start.
#
# Scans motor/ for notes with status: active that have unchecked items
# under a "### P0" heading. Fires once per session (5-min cooldown).
#
# Output is prefixed with VAULT_KEEPER: so agents detect and act on it.

VAULT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
COOLDOWN_FILE="/tmp/vault-agenda-$(id -u).last"
COOLDOWN_SECONDS=300

if [[ -f "$COOLDOWN_FILE" ]]; then
    last_run=$(cat "$COOLDOWN_FILE" 2>/dev/null)
    now=$(date +%s)
    if [[ -n "$last_run" ]] && (( now - last_run < COOLDOWN_SECONDS )); then
        exit 0
    fi
fi

date +%s > "$COOLDOWN_FILE"

alerts=""

# Scan motor/ for active notes with unchecked P0 items
while IFS= read -r file; do
    grep -q '^status: active' "$file" 2>/dev/null || continue

    in_p0=false
    p0_items=""
    while IFS= read -r line; do
        if echo "$line" | grep -q '^### P0'; then
            in_p0=true
            continue
        fi
        if $in_p0; then
            echo "$line" | grep -q '^###' && break
            if echo "$line" | grep -q '^\- \[ \]'; then
                p0_items="${p0_items}\n    ${line}"
            fi
        fi
    done < "$file"

    if [[ -n "$p0_items" ]]; then
        rel="${file#$VAULT_ROOT/}"
        alerts="${alerts}VAULT_KEEPER: P0 tasks due — ${rel}:${p0_items}\n"
    fi
done < <(find "$VAULT_ROOT/motor" -name '*.md' \
    ! -name '_index.md' ! -name '_template.md' 2>/dev/null | sort)

# Also check thalamus (intake) — redundant with vault-keeper-check.sh but useful at session start
thalamus_count=$(find "$VAULT_ROOT/thalamus" -name '*.md' \
    ! -name '_index.md' ! -name '_template.md' 2>/dev/null | wc -l)
if [[ "$thalamus_count" -gt 0 ]]; then
    alerts="${alerts}VAULT_KEEPER: thalamus has ${thalamus_count} items waiting for triage\n"
fi

if [[ -n "$alerts" ]]; then
    echo -e "$alerts"
fi

exit 0
