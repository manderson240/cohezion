#!/usr/bin/env bash
# HOOK_NAME: validate-agent-files
# HOOK_STAGE: post_operation
# HOOK_ACTION: allow
# HOOK_TIMEOUT: 10
# HOOK_DESCRIPTION: Validate agent file frontmatter after Write/Edit
# Non-blocking — prints warning on failure so Claude can self-correct.

set -euo pipefail

# Only act on .claude/agents/*.md files
FILE_PATH="${CLAUDE_FILE_PATH:-}"
if [[ -z "$FILE_PATH" ]] || [[ ! "$FILE_PATH" =~ \.claude/agents/.*\.md$ ]]; then
    exit 0
fi

if [[ ! -f "$FILE_PATH" ]]; then
    exit 0
fi

# Validate the file (non-blocking)
if ! uv run python -c "
from cohezion.validation.agent_schema import validate_agent_file
validate_agent_file('$FILE_PATH')
print('✓ Agent file validated: $FILE_PATH')
" 2>&1; then
    echo "⚠ WARNING: Agent file validation failed for $FILE_PATH"
    echo "  Run: uv run python -c \"from cohezion.validation.agent_schema import validate_agent_file; validate_agent_file('$FILE_PATH')\""
    echo "  to see full error details."
fi

# Always exit 0 — this is advisory, not blocking
exit 0
