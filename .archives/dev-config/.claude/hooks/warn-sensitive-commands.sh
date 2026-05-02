#!/usr/bin/env bash
# PreToolUse: Bash
# Warns when a command may expose or mishandle secrets.

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

WARNINGS=()

# Commands that echo or print known secret variable names
if echo "$CMD" | grep -qE '(echo|printf|print)\s.*(PASSWORD|SECRET|TOKEN|API_KEY|PRIVATE_KEY)'; then
    WARNINGS+=("printing a variable that may contain a secret")
fi

# cat -A / cat -v near .env (reveals non-printable chars including passwords)
# Catches: 'cat -A .env' and pipelines like 'grep ... .env | cat -A'
if echo "$CMD" | grep -qE '(cat\s+-[Av].*\.env|\.env.*\|\s*cat\s+-[Av])'; then
    WARNINGS+=("'cat -A' on .env will expose raw secret values")
fi

# Direct cat of .env
if echo "$CMD" | grep -qE '^\s*cat\s+.*\.env(\s|$)'; then
    WARNINGS+=("reading .env directly may expose secrets in terminal output")
fi

# Passing secrets via command-line args (visible in 'ps')
if echo "$CMD" | grep -qE '\-\-password=\S+|\-\-secret=\S+|\-\-token=\S+'; then
    WARNINGS+=("passing secrets as CLI flags exposes them in process list (ps aux)")
fi

if [ ${#WARNINGS[@]} -gt 0 ]; then
    echo "[warn-sensitive-commands] Security warning:"
    for w in "${WARNINGS[@]}"; do
        echo "  • $w"
    done
    echo "  Proceed only if intentional."
fi

exit 0  # Non-blocking: warn but allow
