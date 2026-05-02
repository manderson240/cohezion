#!/usr/bin/env bash
# Stop: (runs at end of each Ralph Loop iteration)
# Annotates neurons in the graph with Ralph Loop activity.
# Only fires when Ralph Loop is active (.claude/ralph-loop.local.md exists).
# Non-blocking: always exits 0.

# Only run if Ralph Loop is active
RALPH_STATE=".claude/ralph-loop.local.md"
[ -f "$RALPH_STATE" ] || exit 0

# Extract iteration number from YAML frontmatter
ITERATION=$(python3 -c "
import re, sys
try:
    content = open('$RALPH_STATE').read()
    m = re.search(r'iteration:\s*(\d+)', content)
    print(m.group(1) if m else '0')
except:
    print('0')
" 2>/dev/null)

# Extract the prompt (task being worked on)
PROMPT=$(python3 -c "
import sys
try:
    content = open('$RALPH_STATE').read()
    # Prompt is after the YAML frontmatter (after second ---)
    parts = content.split('---', 2)
    if len(parts) >= 3:
        print(parts[2].strip()[:100])
    else:
        print('unknown')
except:
    print('unknown')
" 2>/dev/null)

# Call graph_writer to annotate recently-modified neurons
python3 -c "
import asyncio, sys, os
sys.path.insert(0, os.path.expanduser('~/dev/cohezion/cloud-vault-mcp/src'))
try:
    from mcp_server.graph_writer import upsert_neuron

    # Create/update a Ralph Loop session neuron
    iteration = int('${ITERATION}')
    prompt = '''${PROMPT}'''[:100]

    asyncio.run(upsert_neuron(
        neuron_id=f'neuron:ralph_session_iter{iteration}_md',
        title=f'Ralph Loop iteration {iteration}',
        path='ralph-loop/session',
        cluster='ralph',
        aspect='thinker',
        tags=['ralph-loop', f'iteration-{iteration}'],
        content=f'Ralph Loop iteration {iteration}: {prompt}',
    ))
except Exception as e:
    pass  # Non-blocking
" 2>/dev/null

exit 0
