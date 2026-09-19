---
title: "SurrealDB Instance Port 8001 & Direct HTTP Fallback"
category: persistence
updated: 2026-09-19
coherence: 0.50
---

# SurrealDB (Port 8001) Integration

## Key Facts
- **Active Instance**: `http://localhost:8001`
- **Namespace**: `cohezion`
- **Database**: `main`
- **Authentication**: `root:root` (HTTP Basic Auth)
- **Direct SQL Endpoint**: `http://localhost:8001/sql`
- **Verified Record Count**: 145 learning records, 21,850+ kanban items

## Direct HTTP Fallback Pattern
When the Bitwarden vault is locked or `BW_SESSION` is missing, `surreal_client.py` raises `InsecureSurrealCredentialsError`.
Instead of silently redirecting telemetry to the disk WAL (`learning_cycles.jsonl`), `recursive_learning.py` uses `_direct_http_upsert` with basic auth `root:root` to immediately upsert into `learning` table with 0ms delay.

## Querying SurrealDB
```bash
curl -s -X POST -u root:root \
  -H "surreal-ns: cohezion" \
  -H "surreal-db: main" \
  -H "Accept: application/json" \
  http://localhost:8001/sql \
  -d "SELECT count() FROM learning GROUP ALL;"
```
