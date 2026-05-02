#!/usr/bin/env bash
# PreToolUse: Edit|Write
# Blocks writes to sensitive files (secrets, keys, governance docs).

INPUT=$(cat)

FILE=$(echo "$INPUT" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    print(d.get('tool_input', {}).get('file_path', ''))
except Exception:
    print('')
" 2>/dev/null)

[ -z "$FILE" ] && exit 0

# Resolve to basename for pattern matching
BASE=$(basename "$FILE")

# Blocked patterns - lock files (managed by package manager)
case "$BASE" in
    uv.lock|poetry.lock|package-lock.json|yarn.lock|pnpm-lock.yaml)
        echo "[protect-files] BLOCKED: $BASE is a lock file managed by package manager. Use 'uv lock' instead."
        exit 2
        ;;
esac

# Blocked patterns - secrets and credentials
case "$BASE" in
    .env|.env.*|*.key|*.pem|*.p12|*.pfx|*.secret|*.secrets)
        echo "[protect-files] BLOCKED: $FILE is a secrets/credentials file. Edit manually if intentional."
        exit 2
        ;;
    .secrets.baseline)
        echo "[protect-files] BLOCKED: .secrets.baseline must be managed by detect-secrets, not edited directly."
        exit 2
        ;;
esac

# Blocked governance docs (read-only to Claude)
case "$FILE" in
    */.agent/CONSTITUTION.md|*/.agent/COHEZION_CHARTER.md)
        echo "[protect-files] BLOCKED: Governance documents are read-only. Changes require explicit human review."
        exit 2
        ;;
esac

exit 0
