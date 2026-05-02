#!/usr/bin/env bash
# PreToolUse: Write
# Archives existing plan files before they are overwritten.
# Copies to docs/plans/YYYY-MM-DD-<basename>.md if not already archived today.
# Non-blocking: always exits 0.

INPUT=$(cat)

FILE=$(echo "$INPUT" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    print(d.get('tool_input', {}).get('file_path', ''))
except Exception:
    print('')
" 2>/dev/null) || true

[ -z "$FILE" ] && exit 0

# Only act on plan files in .claude/plans/
case "$FILE" in
    */.claude/plans/*.md) ;;
    *) exit 0 ;;
esac

# Skip if file doesn't exist yet (new plan, nothing to archive)
[ -f "$FILE" ] || exit 0

# Skip tiny files (< 50 bytes = likely empty/placeholder)
FILE_SIZE=$(stat --printf="%s" "$FILE" 2>/dev/null || stat -f%z "$FILE" 2>/dev/null || echo "0")
[ "$FILE_SIZE" -lt 50 ] && exit 0

BASENAME=$(basename "$FILE")
TODAY=$(date +%Y-%m-%d)
ARCHIVE_DIR="docs/plans"
ARCHIVE_NAME="${TODAY}-${BASENAME}"
ARCHIVE_PATH="${ARCHIVE_DIR}/${ARCHIVE_NAME}"

# Skip if already archived today
[ -f "$ARCHIVE_PATH" ] && exit 0

# Ensure archive directory exists
mkdir -p "$ARCHIVE_DIR"

cp "$FILE" "$ARCHIVE_PATH"

cat <<EOF
{"systemMessage": "Archived previous plan to ${ARCHIVE_PATH}"}
EOF

exit 0
