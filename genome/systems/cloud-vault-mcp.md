---
title: "System Card: Cloud Vault MCP"
date: 2026-03-05
version: 1
last_revised: 2026-03-05
tags: [spec, system-card, mcp, infrastructure]
card_type: system
status: active
aspect: knower
neural:
  activation: 0.78
  stage: growing
  synapse_in: 53
  synapse_out: 8
---

# System Card: Cloud Vault MCP

> [!abstract] Summary
> The Cloud Vault MCP server is Cohezion's primary knowledge management interface, exposing 30+ tools across six categories (VaultOps, CompoundOps, ObsidianOps, Teleport, SheetsBridge, SurrealDB) over HTTP MCP protocol. It gives any AI agent — regardless of IDE or model provider — programmatic read/write access to the Obsidian vault, SurrealDB graph database, Google Sheets, and Teleport task sync.

## Identity

| Field | Value |
|-------|-------|
| **Component** | Cloud Vault MCP |
| **Type** | service |
| **Owner** | Cohezion platform team |
| **Status** | active |
| **Version** | 0.3.x |
| **Source** | `~/dev/cohezion/cloud-vault-mcp/` |
| **Deployed As** | systemd service (`cohezion-vault.service`) |

## Connection Details

| Field | Value |
|-------|-------|
| **Host** | `127.0.0.1` |
| **Port** | 8360 |
| **Protocol** | Streamable HTTP (MCP) |
| **Auth** | Bearer token (configured in `~/.claude/mcp.json`) |
| **Health Endpoint** | `GET http://127.0.0.1:8360/health` |
| **MCP Endpoint** | `POST http://127.0.0.1:8360/mcp` |

## Dependencies

| Dependency | Type | Required | Notes |
|-----------|------|----------|-------|
| Python 3.10+ | runtime | Yes | Via venv at `cloud-vault-mcp/.venv/` |
| FastMCP | runtime | Yes | MCP protocol framework |
| Uvicorn + Starlette | runtime | Yes | ASGI web server |
| SurrealDB 3.0 | runtime | No | Graph database — degrades gracefully if down |
| Obsidian vault | runtime | Yes | File system at `~/vaults/cohezion-vault/` |
| Google Sheets API | optional | No | SheetsBridge tools require credentials |
| Cloudflare Tunnel | optional | No | Remote access via persistent tunnel |

## Capabilities

### What It Does
- **VaultOps:** Read, write, search, and cross-link vault notes programmatically
- **CompoundOps:** Log decisions, experiments, patterns; extract context; run the [[experience-feedback-loop]]
- **ObsidianOps:** Manage backlinks, forward links, tags, wiki-link validation
- **SurrealDB:** Query agent context graph (`surrealdb_query`), bulk import papers/concepts
- **Teleport:** Cloud-to-local file sync for cross-environment transfers
- **SheetsBridge:** Batch read/write Google Sheets for research pipeline output

### What It Does NOT Do
- Does not embed content — that's the [[runbook-ollama-mcp-operations|Ollama MCP server]]'s job
- Does not manage the vault's git history
- Does not serve the Obsidian UI

## Configuration

```bash
# Key environment variables (in .env or systemd Environment=)
SURREALDB_URL=http://localhost:8000
SURREALDB_NAMESPACE=cohezion
SURREALDB_DATABASE=vault
SURREALDB_USERNAME=sdb_admin_session43
SURREALDB_PASSWORD=<redacted>
VAULT_PATH=/home/mike-anderson/vaults/cohezion-vault
```

## Monitoring & Health

| Check | Method | Frequency | Alert Threshold |
|-------|--------|-----------|-----------------|
| Server alive | `GET /health` | Continuous (systemd) | Restart on failure |
| SurrealDB connected | `GET /health` → `surrealdb` field | Per-request | Degraded mode if down |
| Tool count | `POST /mcp` → `tools/list` | Manual | Should report 30+ tools |

> [!warning] Known Issue
> `check_surrealdb()` in `health.py:114-164` only hits unauthenticated `/health` — it can report "connected: true" even when query auth fails. Fix tracked in [[2026-03-05-vault-surrealdb-sync-pipeline]] E1-S1.

## Known Limitations

- Health check does not verify authenticated query access (see warning above)
- No rate limiting — relies on Cloudflare tunnel for external access control
- Single-instance only — no horizontal scaling

## Reconstruction Steps

> [!tip] Disaster Recovery
> Steps to rebuild this system from scratch using only vault knowledge.

1. Clone the `cloud-vault-mcp` repo to `~/dev/cohezion/cloud-vault-mcp/`
2. Create Python venv: `python3 -m venv .venv && source .venv/bin/activate`
3. Install: `pip install -e ".[dev]"`
4. Copy `.env` template from this card's Configuration section
5. Set Bearer token in `~/.claude/mcp.json` (see [[cloud-vault-mcp|MCP Server Spec]])
6. Install systemd service: `systemctl --user enable cohezion-vault.service`
7. Start: `systemctl --user start cohezion-vault.service`
8. Verify: `curl http://127.0.0.1:8360/health`

## Security Considerations

- Bearer token auth required for all MCP tool calls
- SurrealDB credentials stored in `.env` (not committed to git)
- Cloudflare tunnel provides TLS for remote access
- No PII stored — vault contains only technical knowledge

## Related

- [[cloud-vault-mcp]] — Concept note with full context and daily references
- [[cloud-vault-mcp|Cloud Vault MCP Spec]] — Detailed tools catalog in `specs/mcp-servers/`
- [[2026-03-05-vault-surrealdb-architecture]] — Architecture ADR for sync pipeline
- [[ide-and-model-providers]] — How different IDEs connect to this server
- [[surrealdb]] — SurrealDB concept note (upstream dependency)
- [[runbook-ollama-mcp-operations|Ollama MCP]] — Companion server for embeddings (System Card: [[ollama]])

## Revision History

| Version | Date | Change |
|---------|------|--------|
| 1 | 2026-03-05 | Initial system card |
