#!/bin/sh
# AI-assisted conventional commit message via llama3.2-1b-FLM at :13305.
#
# Called from .git/hooks/prepare-commit-msg after `entire hooks`.
# Invocation: lemonade_commit_msg.sh <commit-msg-file> [<source>]
#
# Only acts when:
#   - source is empty (fresh commit via editor, no -m flag, no amend)
#   - commit message file has no user-written content yet
#   - Lemonade is reachable at :13305 within 3s
#
# Generates a conventional commit suggestion (one line, ≤72 chars)
# and prepends it to the message file BEFORE the comment block.
# The user sees it in their editor and can accept, edit, or clear it.
#
# Prompt structure: RTF (Role/Task/Format only) — no numbered steps.
# See lemonade-mcp-models-as-tools skill for why thinking-model CoT
# steps must never be used here.
#
# Bypass: LEMONADE_COMMIT_DISABLE=1 git commit ...

set -eu

COMMIT_MSG_FILE="${1:-}"
COMMIT_SOURCE="${2:-}"

[ "${LEMONADE_COMMIT_DISABLE:-}" = "1" ] && exit 0

# Only augment fresh commits (not -m, not amend, not merge, not squash)
[ -n "$COMMIT_SOURCE" ] && exit 0

# Skip if message file not provided (defensive)
[ -z "$COMMIT_MSG_FILE" ] && exit 0
[ ! -f "$COMMIT_MSG_FILE" ] && exit 0

# Skip if user already typed a commit message (non-comment, non-blank lines)
existing=$(grep -v '^#' "$COMMIT_MSG_FILE" | grep -v '^[[:space:]]*$' || true)
[ -n "$existing" ] && exit 0

# Check Lemonade is reachable (3s probe — fail silently if cold)
if ! curl -s --max-time 3 http://localhost:13305/v1/models > /dev/null 2>&1; then
    exit 0
fi

# Gather staged diff (stat + first 2000 chars of diff for better signal)
stat=$(git diff --cached --stat 2>/dev/null | tail -1)
files=$(git diff --cached --name-only 2>/dev/null | head -12 | tr '\n' ' ')
diff_head=$(git diff --cached 2>/dev/null | head -60 | head -c 2000)

[ -z "$files" ] && exit 0

# Call llama3.2-1b-FLM — RTF prompt, not numbered steps
suggestion=$(curl -s --max-time 10 http://localhost:13305/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d "{
    \"model\": \"llama3.2-1b-FLM\",
    \"max_tokens\": 64,
    \"temperature\": 0.1,
    \"messages\": [
      {\"role\": \"system\", \"content\": \"You are a git commit author. Output a single conventional commit message: one line, under 72 chars, format: type(scope): description. Types: feat/fix/refactor/docs/test/chore. No quotes, no trailing period.\"},
      {\"role\": \"user\", \"content\": \"Files: $files\\nSummary: $stat\\nDiff:\\n$diff_head\"}
    ]
  }" 2>/dev/null \
  | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    msg = d['choices'][0]['message']['content'].strip().split('\n')[0]
    # Strip surrounding quotes if model added them
    msg = msg.strip('\"').strip(\"'\")
    if len(msg) > 5:
        print(msg)
except Exception:
    pass
" 2>/dev/null)

[ -z "$suggestion" ] && exit 0

# Prepend suggestion as first line in the editor template
tmpfile=$(mktemp)
printf '%s\n' "$suggestion" > "$tmpfile"
printf '\n' >> "$tmpfile"
cat "$COMMIT_MSG_FILE" >> "$tmpfile"
mv "$tmpfile" "$COMMIT_MSG_FILE"
