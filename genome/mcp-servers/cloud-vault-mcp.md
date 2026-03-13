---
title: "Cloud Vault MCP Server"
date: 2026-03-05
version: 1
last_revised: 2026-03-05
tags: [spec, mcp-server, infrastructure]
source: "~/.claude/mcp.json + ~/dev/cohezion/cloud-vault-mcp/"
status: active
aspect: knower
neural:
  activation: 0.66
  stage: growing
  synapse_in: 0
  synapse_out: 3
---

# Cloud Vault MCP Server

> [!abstract] Purpose
> Programmatic access to the Cohezion vault — read, write, search, graph query, and sync operations over MCP protocol.

## Connection

| Field | Value |
|-------|-------|
| Type | HTTP (Streamable HTTP) |
| URL | `http://127.0.0.1:8360` |
| Auth | Bearer token: `MCP_API_KEY` from `.env` |
| Service | `cohezion-vault.service` (systemd user service) |
| Source | `~/dev/cohezion/cloud-vault-mcp/` |

## MCP Config

```json
{
  "cloud-vault-mcp": {
    "type": "http",
    "url": "http://127.0.0.1:8360",
    "headers": {
      "Authorization": "Bearer <MCP_API_KEY>"
    }
  }
}
```

## Tools Catalog

### VaultOps (filesystem)

| Tool | Purpose |
|------|---------|
| `vault_read` | Read a note's content |
| `vault_write` | Create or overwrite a note |
| `vault_edit` | Apply surgical edits (find/replace, append, prepend, insert at heading) |
| `vault_search` | Full-text search across vault |
| `vault_list` | List notes in a directory |
| `vault_tags` | Query by tags |

### SurrealDB (graph database)

| Tool | Purpose |
|------|---------|
| `surrealdb_query` | Execute raw SurrealQL queries |
| `surrealdb_import_papers` | Bulk import papers/ to SurrealDB |
| `surrealdb_import_concepts` | Bulk import concepts/ to SurrealDB |
| `surrealdb_start_watching` | Start file watcher for real-time sync |
| `surrealdb_stop_watching` | Stop file watcher |

### Agent Context

| Tool | Purpose |
|------|---------|
| `agent_start_session` | Create agent session node in SurrealDB |
| `agent_log_decision` | Log a decision with reasoning chain |
| `agent_log_artifact` | Log an artifact produced by agent |

### Health

| Tool | Purpose |
|------|---------|
| `/health` endpoint | Returns status of vault, SurrealDB, Ollama, disk, memory |

## Dependencies

| Dependency | Port | Service |
|------------|------|---------|
| SurrealDB 3.0 | 8000 | `cohezion-surreal.service` |
| Ollama | 11434 | `ollama.service` |
| Vault filesystem | — | `/home/mike-anderson/vaults/cohezion-vault` |

## Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `MCP_API_KEY` | — | Bearer token auth |
| `MCP_PORT` | 8360 | Server port |
| `VAULT_PATH` | `/vault` | Vault directory |
| `SURREALDB_URL` | `http://localhost:8000` | SurrealDB endpoint |
| `SURREALDB_USERNAME` | `root` | SurrealDB auth |
| `SURREALDB_PASSWORD` | `root` | SurrealDB auth |
| `SURREALDB_NAMESPACE` | `cohezion` | SurrealDB namespace |
| `SURREALDB_DATABASE` | `vault` | SurrealDB database |
| `OLLAMA_URL` | `http://localhost:11434` | Ollama endpoint |

## Reconstruction

To rebuild from scratch:
```bash
cd ~/dev/cohezion/cloud-vault-mcp
uv pip install -e .
# Copy .env from .env.example, fill in values
cp .env.example .env
# Start service
systemctl --user start cohezion-vault.service
```

## Related

- [[2026-03-05-vault-surrealdb-sync-pipeline]] — Sync pipeline PRD
- [[surrealdb]] — SurrealDB concept
- [[cloud-vault-mcp]] — Concept note
