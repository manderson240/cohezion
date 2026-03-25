#!/usr/bin/env bash
# PostToolUse: mcp__cohezion-vault__vault_write|mcp__cohezion-vault__vault_edit
# Syncs vault note changes to the neuron graph in SurrealDB.
# Non-blocking: always exits 0. Graph sync failure never blocks vault writes.

INPUT=$(cat)

# Extract vault-relative path from tool_input
PATH_VAL=$(echo "$INPUT" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    print(d.get('tool_input', {}).get('path', ''))
except Exception:
    print('')
" 2>/dev/null)

# Skip if no path or if it's a daily/session note (too noisy)
[ -z "$PATH_VAL" ] && exit 0
case "$PATH_VAL" in
    daily/*|sessions/*|teleport/*) exit 0 ;;
esac

# Only sync markdown files
[[ "$PATH_VAL" != *.md ]] && exit 0

# Derive cluster from first path component
CLUSTER=$(echo "$PATH_VAL" | cut -d'/' -f1)
case "$CLUSTER" in
    cortex) CLUSTER="cortex" ;;
    cerebellum|patterns|decisions|experiments) CLUSTER="cerebellum" ;;
    *) CLUSTER="cortex" ;;  # Default to cortex for uncategorized
esac

VAULT_ROOT="$HOME/vaults/cohezion-vault"
FULL_PATH="$VAULT_ROOT/$PATH_VAL"
VENV_PYTHON="$HOME/dev/cohezion/cloud-vault-mcp/.venv/bin/python3"

# Fallback to system python3 if venv not found
[ -x "$VENV_PYTHON" ] || VENV_PYTHON="python3"

# Call graph_writer to upsert the neuron
"$VENV_PYTHON" -c "
import asyncio, sys, os, re

sys.path.insert(0, os.path.expanduser('~/dev/cohezion/cloud-vault-mcp/src'))
try:
    from mcp_server.graph_writer import upsert_neuron, slugify
    from pathlib import Path

    vault_path = '$PATH_VAL'
    full_path = Path('$FULL_PATH')
    cluster = '$CLUSTER'

    if not full_path.is_file():
        sys.exit(0)

    content = full_path.read_text(encoding='utf-8')
    stem = full_path.stem  # e.g. 'agent-architecture'
    neuron_id = f'neuron:{slugify(stem)}_md'
    title = stem.replace('-', ' ').replace('_', ' ').title()

    # Extract tags from YAML frontmatter if present
    tags = [cluster]
    if content.startswith('---'):
        parts = content.split('---', 2)
        if len(parts) >= 3:
            fm = parts[1]
            # Extract tags line
            m = re.search(r'tags:\s*\[([^\]]*)\]', fm)
            if m:
                for t in m.group(1).split(','):
                    t = t.strip().strip('\"').strip(\"'\")
                    if t:
                        tags.append(t)
            # Extract title if present
            m = re.search(r'title:\s*[\"'\''](.*?)[\"'\'']', fm)
            if not m:
                m = re.search(r'title:\s*(.+)', fm)
            if m:
                title = m.group(1).strip()

    # Derive aspect from cluster
    aspect = 'connective'
    if cluster == 'cortex':
        aspect = 'knower'
    elif cluster == 'cerebellum':
        aspect = 'thinker'

    asyncio.run(upsert_neuron(
        neuron_id=neuron_id,
        title=title,
        path=vault_path,
        cluster=cluster,
        aspect=aspect,
        tags=tags,
        content=content,
    ))
except Exception as e:
    pass  # Non-blocking: graph sync failure is not critical
" 2>/dev/null

exit 0
