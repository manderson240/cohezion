#!/usr/bin/env bash
# CI sync check: ensure the canonical router policy and the vault-tool mirror
# are byte-identical and valid JSON.
set -euo pipefail

usage() {
  cat >&2 <<'USAGE'
Usage: check_router_sync.sh [REPO_JSON] [VAULT_JSON]

If REPO_JSON is omitted, derive it from COHEZION_REPO (default: ~/dev/cohezion).
If VAULT_JSON is omitted, derive it from COHEZION_VAULT (default: ~/vaults/cohezion-vault).
USAGE
  exit 1
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
fi

REPO_BASE="${COHEZION_REPO:-${HOME}/dev/cohezion}"
VAULT_BASE="${COHEZION_VAULT:-${HOME}/vaults/cohezion-vault}"

REPO_JSON="${1:-${REPO_BASE}/config/router/cohezion-router.json}"
VAULT_JSON="${2:-${VAULT_BASE}/tools/cohezion-engine/config/router/cohezion-router.json}"

if [ ! -f "$REPO_JSON" ]; then
  echo "Missing repo router JSON: $REPO_JSON" >&2
  echo "Set COHEZION_REPO or pass the path explicitly." >&2
  exit 1
fi

if [ ! -f "$VAULT_JSON" ]; then
  echo "Missing vault router JSON: $VAULT_JSON" >&2
  echo "Set COHEZION_VAULT or pass the path explicitly." >&2
  exit 1
fi

# Validate both files parse as JSON.
if ! python3 -m json.tool "$REPO_JSON" >/dev/null 2>&1; then
  echo "Repo router JSON is not valid JSON: $REPO_JSON" >&2
  exit 1
fi

if ! python3 -m json.tool "$VAULT_JSON" >/dev/null 2>&1; then
  echo "Vault router JSON is not valid JSON: $VAULT_JSON" >&2
  exit 1
fi

# Schema sanity: candidates and default_model must be subsets of components.
REPO_JSON="$REPO_JSON" VAULT_JSON="$VAULT_JSON" python3 - >&2 <<'PYEOF'
import json, os, sys
repo_path = os.environ.get("REPO_JSON")
vault_path = os.environ.get("VAULT_JSON")
repo = json.load(open(repo_path))
vault = json.load(open(vault_path))
for label, policy in [("repo", repo), ("vault", vault)]:
    components = set(policy.get("components", []))
    routing = policy.get("routing", {})
    candidates = set(routing.get("candidates", []))
    default = routing.get("default_model")
    unknown = candidates - components
    if unknown:
        print(f"{label}: candidates not in components: {sorted(unknown)}", file=sys.stderr)
        sys.exit(1)
    if default not in components:
        print(f"{label}: default_model '{default}' not in components", file=sys.stderr)
        sys.exit(1)
PYEOF

if ! diff -q "$REPO_JSON" "$VAULT_JSON" >/dev/null; then
  echo "Router JSON mismatch:" >&2
  diff -u "$REPO_JSON" "$VAULT_JSON" >&2
  echo "To sync: cp '$REPO_JSON' '$VAULT_JSON'" >&2
  exit 1
fi

echo "Router JSON sync OK"
