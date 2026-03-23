---
name: graphrag-execute-surreal-hardcoded-url
description: |
  Fix for GraphRAGImporter silently failing all imports with "All connection
  attempts failed" despite SurrealDB being reachable. Use when: (1) reimport_vault.py
  runs for 30-45 minutes and reports 0/N imported for every directory, (2) the
  error is "All connection attempts failed" but curl to SurrealDB returns 200,
  (3) post-import count query succeeds but per-file imports all fail, (4) you
  passed surrealdb_url=http://localhost:8001 to GraphRAGImporter but it still hits
  :8000. Root cause: execute_surreal_async in graphrag_helpers.py has a hardcoded
  "http://localhost:8000/sql" that ignores the surrealdb_url parameter entirely.
author: Claude Code
version: 1.0.0
---

# GraphRAG execute_surreal_async Hardcoded URL Bug

## Problem

`reimport_vault.py` runs for 40+ minutes, then reports `0/355 imported, 355 failed`.
Every file import fails with `"SurrealDB query failed after 3 attempts: All connection
attempts failed"`. The post-import count query to SurrealDB succeeds (200 OK), and
`vault_memory` table either doesn't exist or has 0 records.

## Root Cause

`execute_surreal_async` in `src/mcp_server/graphrag_helpers.py` has a **hardcoded URL**:

```python
# graphrag_helpers.py — the bug
async def execute_surreal_async(
    query: str,
    client: httpx.AsyncClient,
    namespace: str = "cohezion",
    database: str = "vault",
    auth: tuple = ("root", "root"),
    max_retries: int = 3,
) -> list[dict[str, Any]]:
    for attempt in range(max_retries):
        response = await client.post(
            "http://localhost:8000/sql",   # ← HARDCODED — ignores surrealdb_url
            ...
        )
```

`GraphRAGImporter.__init__` stores `self.surrealdb_url` but this value never reaches
the helper function. The `count_records()` function in `reimport_vault.py` uses its own
`httpx.AsyncClient` directly to the correct port, so it succeeds — making the failure
even more confusing (post-import count works; per-file imports all fail).

## Diagnosis

```bash
# Confirm SurrealDB is on 8001, not 8000
ss -tlnp | grep -E "800[01]"

# Confirm vault_memory table is empty despite successful count query
curl -s -X POST http://localhost:8001/sql \
  -H "surreal-ns: cohezion" -H "surreal-db: vault" \
  -H "Content-Type: text/plain" -u root:root \
  -d "SELECT count() FROM vault_memory GROUP ALL;"
# Returns: "The table 'vault_memory' does not exist" → confirm 0 imports

# Find the hardcoded URL
grep -n "localhost:8000" ~/dev/cohezion/cloud-vault-mcp/src/mcp_server/graphrag_helpers.py
```

## Fix

Add a `url` parameter to `execute_surreal_async` with the correct default, and wire
the importer's `surrealdb_url` through to each call:

```python
# graphrag_helpers.py — fix
async def execute_surreal_async(
    query: str,
    client: httpx.AsyncClient,
    namespace: str = "cohezion",
    database: str = "vault",
    auth: tuple = ("root", "root"),
    max_retries: int = 3,
    url: str = "http://localhost:8001/sql",   # ← parameterized, default corrected
) -> list[dict[str, Any]]:
    for attempt in range(max_retries):
        response = await client.post(
            url,   # ← uses parameter
            ...
        )
```

```python
# graphrag_import.py — wire through in import_document()
results = await execute_surreal_async(
    query, self.http_client, self.namespace, self.database,
    url=self.surrealdb_url.rstrip("/") + "/sql",
)
```

All other callers within `graphrag_helpers.py` (lines ~116, 171, 188, 228) use the
default, which is now correct. No changes needed to those callsites.

## Verification

```bash
# Re-run reimport — should show success counts
cd ~/dev/cohezion/cloud-vault-mcp
.venv/bin/python scripts/reimport_vault.py 2>&1 | tail -15
# Expect: cortex: 255/255 imported, 0 failed

# Verify neurons in SurrealDB
curl -s -X POST http://localhost:8001/sql \
  -H "surreal-ns: cohezion" -H "surreal-db: vault" \
  -H "Content-Type: text/plain" -u root:root \
  -d "SELECT type, count() FROM vault_memory GROUP BY type;"
# Expect: [{'count': 343, 'type': 'neuron'}]
```

## Why the Error Is Misleading

The "connection failed" error makes it look like SurrealDB is down. But SurrealDB IS
up — just on a different port. The reimport script's own `count_records()` function
uses the correct port directly, so it succeeds, adding to the confusion.

The tell: **post-import count works but all per-file imports fail** → hardcoded URL
in helper layer.

## Context

- SurrealDB runs on port **8001** in this setup (not the default 8000)
- `run_mcp.py` sets `SURREALDB_URL=http://localhost:8001` — correct
- `reimport_vault.py` passes `surrealdb_url="http://localhost:8001"` to
  `GraphRAGImporter` — correct
- `GraphRAGImporter` stores it in `self.surrealdb_url` — correct
- `execute_surreal_async` ignores it entirely — the bug
