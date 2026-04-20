#!/usr/bin/env bash
# Pre-Flight RAG Hook - Memory Injection for Cohezion Agents
# Logic: Analyzes current context and injects the 3 most relevant learnings.

PROJECT_ROOT=$(git rev-parse --show-toplevel)
CONTEXT_FILE="$PROJECT_ROOT/.claude/session_context.md"

# 1. Determine current context keywords (branch + recent activity)
BRANCH=$(git rev-parse --abbrev-ref HEAD)
RECENT_CHANGES=$(git log -n 5 --name-only --pretty=format: | sort -u | xargs basename -s .py -s .md | tr '\n' ' ')

# 2. Run semantic search using the internal knowledge engine
# We use 'uv run' to ensure we hit the right environment
LEARNINGS=$(uv run python -c "
from cohezion.knowledge_graph.query_engine import KnowledgeGraphQueryEngine
from pathlib import Path
import asyncio

async def run():
    engine = KnowledgeGraphQueryEngine(knowledge_dir='$PROJECT_ROOT/src/cohezion/knowledge_graph')
    query = '$BRANCH $RECENT_CHANGES'
    results = engine.search_knowledge(query, top_k=3)
    
    print('# 🧠 PRE-FLIGHT MEMORY INJECTION')
    print('The following past learnings are highly relevant to your current workspace context:')
    for r in results:
        print(f'\n## {r[\"title\"]}')
        print(f'Source: {r[\"path\"]}')
        print(f'{r[\"snippet\"]}')
        
asyncio.run(run())
")

# 3. Save to session context file for the agent to read
echo "$LEARNINGS" > "$CONTEXT_FILE"

echo "✅ Pre-flight memory injection complete. Relevant learnings saved to $CONTEXT_FILE"
