#!/usr/bin/env bash
# PostToolUse: Edit|Write
# Validates agent files and skill registry after they're written.
# Non-blocking: warns but always exits 0.

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
[ -f "$FILE" ] || exit 0

BASE=$(basename "$FILE")

# Validate agent markdown files have required frontmatter
case "$FILE" in
    */.claude/agents/*.md|*/skills/*.md)
        if ! head -1 "$FILE" | grep -q '^---'; then
            echo "[validate-agent-files] Warning: $BASE is missing YAML frontmatter (should start with ---)."
        fi
        ;;
esac

# Validate skill_registry.json is valid JSON
case "$BASE" in
    skill_registry.json)
        if ! python3 -c "import json,sys; json.load(open(sys.argv[1]))" "$FILE" 2>/dev/null; then
            echo "[validate-agent-files] ERROR: $BASE contains invalid JSON. Fix before committing."
        fi
        ;;
esac

# Validate pyproject.toml is valid TOML
case "$BASE" in
    pyproject.toml)
        if python3 -c "import tomllib" 2>/dev/null; then
            if ! python3 -c "import tomllib,sys; tomllib.load(open(sys.argv[1],'rb'))" "$FILE" 2>/dev/null; then
                echo "[validate-agent-files] ERROR: pyproject.toml contains invalid TOML."
            fi
        fi
        ;;
esac

exit 0
