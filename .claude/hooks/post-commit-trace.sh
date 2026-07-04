#!/usr/bin/env bash
# post-commit-trace.sh — emit traceability record for each git commit.
# Parses [step: N.N] tags from commit message. Always exits 0.
set -euo pipefail

HASH=$(git rev-parse HEAD 2>/dev/null) || exit 0
MSG=$(git log -1 --pretty=%s 2>/dev/null) || exit 0

# Get active plan slug from cz CLI
SLUG=$(cz plan status --json 2>/dev/null \
    | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('slug',''))" 2>/dev/null) || SLUG=""

# Extract [step: N.N] or [step: N.Na] patterns from commit message
STEPS=($(echo "$MSG" | grep -oE '\[step: [0-9]+\.[0-9]+[a-z]?\]' | grep -oE '[0-9]+\.[0-9]+[a-z]?'))

if [ -z "$SLUG" ] && [ ${#STEPS[@]} -eq 0 ]; then
    exit 0
fi

# Fire-and-forget: background the trace call so it never blocks git
(uv run python -m cohezion.traceability.record_commit "$HASH" "$MSG" "$SLUG" "${STEPS[@]}" 2>/dev/null) &

exit 0
