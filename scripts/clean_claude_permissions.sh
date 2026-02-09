#!/usr/bin/env bash
# Reset .claude/settings.local.json to hooks-only, stripping accumulated one-off permissions.
# The canonical allow/deny rules live in .claude/settings.json (git-tracked).
#
# Usage: ./scripts/clean_claude_permissions.sh
#        ./scripts/clean_claude_permissions.sh --dry-run

set -euo pipefail

REPO_ROOT="$(git -C "$(dirname "$0")" rev-parse --show-toplevel)"
LOCAL_SETTINGS="$REPO_ROOT/.claude/settings.local.json"

if [[ ! -f "$LOCAL_SETTINGS" ]]; then
    echo "No settings.local.json found — nothing to clean."
    exit 0
fi

# Count current allow rules (0 if no permissions block)
current_allows=$(python3 -c "
import json, sys
with open('$LOCAL_SETTINGS') as f:
    data = json.load(f)
allows = data.get('permissions', {}).get('allow', [])
denies = data.get('permissions', {}).get('deny', [])
print(f'{len(allows)} allow, {len(denies)} deny')
" 2>/dev/null || echo "0 allow, 0 deny")

echo "Current accumulated rules in settings.local.json: $current_allows"

if [[ "${1:-}" == "--dry-run" ]]; then
    echo "[dry-run] Would strip all permissions, keeping hooks only."
    exit 0
fi

# Extract hooks, drop permissions
python3 -c "
import json
with open('$LOCAL_SETTINGS') as f:
    data = json.load(f)
# Keep only hooks
clean = {}
if 'hooks' in data:
    clean['hooks'] = data['hooks']
with open('$LOCAL_SETTINGS', 'w') as f:
    json.dump(clean, f, indent=2)
    f.write('\n')
"

echo "Cleaned. Canonical rules remain in .claude/settings.json (git-tracked)."
echo "settings.local.json now contains hooks only."
