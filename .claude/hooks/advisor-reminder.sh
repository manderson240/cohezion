#!/bin/bash
# SessionStart hook — reminds the user to run `/advisor` at session start.
#
# `/advisor` is session-scoped in Claude Code (v2.1.x) — there is no persistent
# config. This hook surfaces a one-line nudge so the user doesn't forget to
# configure the secondary-opinion model for the current session.
#
# Silent when the reminder would be noise (e.g. in -p/headless mode).

set -u

# Read the SessionStart payload from stdin (we don't need it, but drain it so
# the Claude Code side doesn't see EPIPE).
INPUT="$(cat)"

# Detect whether we're in interactive mode. Headless/print-mode sessions
# shouldn't get the reminder because they can't type slash commands.
# SESSION_MODE is surfaced by Claude Code ≥2.0; fallback heuristic if unset.
MODE="${CLAUDE_CODE_SESSION_MODE:-interactive}"
if [ "$MODE" != "interactive" ]; then
    exit 0
fi

# One-line reminder, printed to stderr so it surfaces without polluting the
# SessionStart JSON response.
echo "💡 /advisor — configure a secondary-opinion model (Sonnet or Opus) for this session." >&2
echo "   Session-scoped; must be re-run each time. See https://platform.claude.com/docs/en/agents-and-tools/tool-use/advisor-tool" >&2

exit 0
