---
title: "System Card: SurrealDB 3.0"
date: 2026-03-05
version: 1
last_revised: 2026-03-05
tags: [spec, system-card, surrealdb, database, infrastructure]
card_type: system
status: active
aspect: knower
neural:
  activation: 0.79
  stage: growing
  synapse_in: 201
  synapse_out: 8
---

# System Card: SurrealDB 3.0

> [!abstract] Summary
> SurrealDB 3.0 is Cohezion's multi-model database, serving as the agent context graph backend. It stores vault notes as typed records with schema-level relationships, enabling graph traversal queries that link papers, concepts, decisions, and lessons. Agents query it via the Cloud Vault MCP's SurrealDB tools.

## Identity

| Field | Value |
|-------|-------|
| **Component** | SurrealDB |
| **Type** | database |
| **Owner** | Cohezion platform team |
| **Status** | active |
| **Version** | 3.0.x |
| **Source** | Binary at `/usr/local/bin/surreal` |
| **Deployed As** | systemd service (`cohezion-surreal.service`) |

## Connection Details

| Field | Value |
|-------|-------|
| **Host** | `localhost` |
| **Port** | 8000 |
| **Protocol** | HTTP REST / WebSocket |
| **Auth** | Basic auth (`sdb_admin_session43`) |
| **Health Endpoint** | `GET http://localhost:8000/health` |
| **SQL Endpoint** | `POST http://localhost:8000/sql` |
| **Namespace** | `cohezion` |
| **Database** | `vault` |

## Dependencies

| Dependency | Type | Required | Notes |
|-----------|------|----------|-------|
| RocksDB | storage | Yes | Embedded storage engine |
| Linux x86_64 | runtime | Yes | Binary platform |
| systemd | deployment | Yes | Service management |

## Capabilities

### What It Does
- **Document store:** Vault notes as typed records (`paper`, `concept`, `decision`, `lesson`, `pattern`, `experiment`, `project`, `spec`)
- **Graph database:** Wiki-links as typed edges (`RELATE concept:X->links->concept:Y`)
- **Vector search:** HNSW indexes for semantic similarity (SurrealDB 3.0 native)
- **Change Feeds:** 90-day temporal audit trail of all mutations
- **Computed fields:** Auto-derived metadata (link counts, staleness flags)
- **SurrealQL:** Full query language with graph traversal (`->links->` syntax)

### What It Does NOT Do
- Does not manage the vault filesystem (that's Obsidian + git)
- Does not generate embeddings (that's [[ollama]])
- Does not serve the MCP protocol directly (that's [[cloud-vault-mcp]])

### Current Data

| Table | Records | Description |
|-------|---------|-------------|
| `paper` | 102 | Research paper records |
| `concept` | 317 | Concept definitions |
| `links` | 1,458 | Typed edge relationships |

## Configuration

```bash
# systemd service: cohezion-surreal.service
ExecStart=/usr/local/bin/surreal start \
  --bind 0.0.0.0:8000 \
  --user sdb_admin_session43 \
  --pass <redacted> \
  rocksdb://~/.surrealdb/cohezion

# Query headers required
Authorization: Basic <base64(user:pass)>
surreal-ns: cohezion
surreal-db: vault
```

## Monitoring & Health

| Check | Method | Frequency | Alert Threshold |
|-------|--------|-----------|-----------------|
| Server alive | `GET /health` → 200 | Continuous (systemd) | Restart on failure |
| Auth working | `POST /sql` with `INFO FOR DB` | Periodic | Alert if auth fails |
| Record count | `SELECT count() FROM paper GROUP ALL` | Daily | Alert if drops >10% |

## Performance (SurrealDB 3.0)

| Metric | Value | Notes |
|--------|-------|-------|
| Graph query speedup | 8-22x vs 2.x | SurrealDB 3.0 graph engine rewrite |
| HNSW vector search | Native | No external vector DB needed |
| Change Feed retention | 90 days | Configurable |
| Storage engine | RocksDB | Persistent, crash-safe |

## Known Limitations

- Single-node deployment (no clustering in current setup)
- No automated backup schedule yet
- Health endpoint is unauthenticated — doesn't prove query auth works
- 3D graph plugin (`SurrealDBClient.ts`) missing auth headers — E1-S3 in [[2026-03-05-vault-surrealdb-sync-pipeline]]

## Reconstruction Steps

> [!tip] Disaster Recovery
> Steps to rebuild this system from scratch using only vault knowledge.

1. Install SurrealDB 3.0: `curl -sSf https://install.surrealdb.com | sh`
2. Create data directory: `mkdir -p ~/.surrealdb/cohezion`
3. Start with credentials: `surreal start --bind 0.0.0.0:8000 --user sdb_admin_session43 --pass <pass> rocksdb://~/.surrealdb/cohezion`
4. Create namespace/database: `DEFINE NAMESPACE cohezion; USE NS cohezion; DEFINE DATABASE vault;`
5. Define tables: `paper`, `concept`, `decision`, `lesson`, `pattern`, `experiment`, `project`, `spec`
6. Run bulk import via MCP: `surrealdb_import_papers` + `surrealdb_import_concepts`
7. Install systemd service: `systemctl --user enable cohezion-surreal.service`
8. Verify: `curl -u sdb_admin_session43:<pass> -H "surreal-ns: cohezion" -H "surreal-db: vault" http://localhost:8000/sql -d "INFO FOR DB"`

## Security Considerations

- Credentials stored in systemd service file and `.env` (not in git)
- Bound to `0.0.0.0` but firewalled to localhost access only
- No TLS on localhost (Cloudflare tunnel provides TLS for remote)

## Related

- [[surrealdb]] — Concept note with technical details and SurrealQL patterns
- [[surrealdb-graph-databases]] — Research paper on SurrealDB graph capabilities
- [[2026-03-05-vault-surrealdb-architecture]] — Architecture ADR for sync pipeline
- [[2026-03-05-vault-surrealdb-sync-pipeline]] — PRD with epics and stories
- [[lesson-05-surrealdb]] — SurrealDB query patterns and syntax gotchas
- [[lesson-surrealdb-schema-design]] — Record-centric schema design lesson

## Revision History

| Version | Date | Change |
|---------|------|--------|
| 1 | 2026-03-05 | Initial system card |
