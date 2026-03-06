#!/usr/bin/env bash
# seed_bitwarden.sh — One-time setup: store all Cohezion secrets in Bitwarden.
#
# Usage: ./scripts/secrets/seed_bitwarden.sh
#
# Run this once per machine (or after a Bitwarden account reset) to populate
# all secrets. After seeding, use restore_env.sh to regenerate .env at any time.
#
# Requires:
#   - Bitwarden CLI at ~/.local/bin/bw (or bw in PATH)
#   - An active, unlocked Bitwarden session
#   - python3 in PATH

set -euo pipefail

BW="${BW_PATH:-${HOME}/.local/bin/bw}"
if [[ ! -x "$BW" ]]; then
    BW="$(command -v bw 2>/dev/null || true)"
fi

if [[ -z "$BW" ]]; then
    echo "ERROR: Bitwarden CLI (bw) not found." >&2
    echo "Install: https://bitwarden.com/help/cli/" >&2
    exit 1
fi

STATUS=$("$BW" status 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('status','unknown'))" 2>/dev/null || echo "unknown")

if [[ "$STATUS" == "unauthenticated" ]]; then
    echo "Not logged in. Run: bw login" >&2
    exit 1
fi

if [[ "$STATUS" == "locked" ]]; then
    echo "Unlocking vault..."
    BW_SESSION=$("$BW" unlock --raw)
    export BW_SESSION
fi

# Create or update a Bitwarden login item.
# If the item already exists, it is skipped (no overwrite) unless --force is passed.
upsert_item() {
    local name="$1"
    local value="$2"

    # Check if item already exists
    local existing
    existing=$("$BW" get item "$name" 2>/dev/null || true)

    if [[ -n "$existing" ]]; then
        echo "  SKIP  '${name}' already exists (use 'bw edit item' to update)"
        return
    fi

    # Build item JSON and create
    local json
    json=$(python3 -c "
import json, sys
item = {
    'organizationId': None,
    'folderId': None,
    'type': 1,
    'name': sys.argv[1],
    'notes': 'Managed by cohezion/scripts/secrets/seed_bitwarden.sh',
    'favorite': False,
    'login': {
        'username': '',
        'password': sys.argv[2],
        'uris': []
    }
}
print(json.dumps(item))
" "$name" "$value")

    local encoded
    encoded=$("$BW" encode <<< "$json")
    "$BW" create item "$encoded" > /dev/null
    echo "  ADDED '${name}'"
}

prompt_secret() {
    local prompt="$1"
    local var_name="$2"
    local value=""

    # If the env var is already set, offer to use it
    if [[ -n "${!var_name:-}" ]]; then
        echo "  Using ${var_name} from environment."
        value="${!var_name}"
    else
        read -r -s -p "  ${prompt}: " value
        echo ""
    fi
    echo "$value"
}

echo "=== Cohezion Bitwarden Seed ==="
echo "This will create Bitwarden items for all Cohezion secrets."
echo "Items that already exist will be skipped."
echo ""

# Secrets to seed. Format: "bw-item-name|env-var-name|human-readable prompt"
ITEMS=(
    "cohezion/anthropic-api-key|ANTHROPIC_API_KEY|Anthropic API key (sk-ant-...)"
    "cohezion/api-key|COHEZION_API_KEY|Cohezion internal API key"
    "cohezion/secret-key|COHEZION_SECRET_KEY|JWT signing secret (long random string)"
    "cohezion/mcp-api-key|MCP_API_KEY|MCP server API key"
    "cohezion/cloud-vault-api-key|CLOUD_VAULT_API_KEY|Cloud Vault API key"
    "cohezion/google-email|GOOGLE_EMAIL|Gmail sender address"
    "cohezion/notification-password|NOTIFICATION_PASSWORD|Gmail app password"
    "cohezion/ngrok-api-key|NGROK_API_KEY|ngrok API key"
    "cohezion/surreal-password|SURREAL_PASSWORD|SurrealDB root password"
    "cohezion/surrealdb-username|SURREALDB_USERNAME|SurrealDB username"
    "cohezion/surrealdb-password|SURREALDB_PASSWORD|SurrealDB password"
)

for entry in "${ITEMS[@]}"; do
    IFS="|" read -r bw_name env_var prompt <<< "$entry"
    echo "[ ${bw_name} ]"
    value=$(prompt_secret "$prompt" "$env_var")
    if [[ -n "$value" ]]; then
        upsert_item "$bw_name" "$value"
    else
        echo "  SKIP  (no value provided)"
    fi
    echo ""
done

echo "Seeding complete."
echo "Run './scripts/secrets/restore_env.sh' to regenerate your .env file."
