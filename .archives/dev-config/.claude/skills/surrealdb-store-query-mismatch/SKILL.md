---
name: surrealdb-store-query-mismatch
description: |
  Fix for SurrealDB MCP tools appearing to succeed (returning IDs) but query
  returning empty results. Use when: (1) mcp__cohezion-surreal__store_learning
  returns {"id": "learning_xxx", ...} but mcp__cohezion-surreal__query_learnings
  returns {"result": []}, (2) store_node succeeds but query_nodes finds nothing,
  (3) any cohezion-surreal MCP write appears to work but reads return empty.
  Key insight: SurrealDB MCP server accepts writes without a live DB connection
  but queries silently return empty when ws://localhost:8000 is not running.
author: Claude Code
version: 1.0.0
---

# SurrealDB Store/Query Mismatch

## Problem

The `cohezion-surreal` MCP tools (`store_learning`, `store_node`, etc.) return
success responses with IDs, but subsequent queries return empty results. The
writes appear to succeed but nothing is persisted.

## Root Cause

SurrealDB must be running at `ws://localhost:8000` for persistence. The MCP
server may accept store calls and generate IDs (in-memory or no-op) without
an active DB connection, but queries against a non-running DB return empty.

## Diagnosis

```bash
# Check if SurrealDB is running
ss -tlnp | grep 8000
# or
curl -s http://localhost:8000/health 2>/dev/null && echo "RUNNING" || echo "NOT RUNNING"
```

If not running, that's why queries return empty.

## Fix

```bash
# Start SurrealDB (adjust for your setup)
surreal start --log trace --user root --pass root memory &
# or via docker:
docker run -p 8000:8000 surrealdb/surrealdb:latest start --user root --pass root memory
```

After starting, re-run the `store_learning` calls and verify with `query_learnings`.

## Workaround (When DB Cannot Be Started)

Treat `store_learning` success IDs as evidence that the MCP server received the
data. Document the learning IDs so they can be re-stored when SurrealDB is
available. The store calls are not lost — they just need to be replayed.

Store ID format: `learning_<hex>` (e.g., `learning_5cc828483474`)

## Verification

```python
# After fixing, verify with min_score filter:
mcp__cohezion-surreal__query_learnings(min_score=0.8, limit=10)
# Should return non-empty list of stored learnings
```

## Known Limitation

`store_node` has a separate bug: `UniverseNode.__init__() missing 1 required
positional argument: 'id'` — the `id` param is required server-side but absent
from the JSON schema. Use `store_learning` instead for knowledge persistence.
