---
title: "Patterns/Troubleshooting Mcp Infrastructure"
date: 2026-02-19
tags: [concept]
aspect: knower
neural:
  activation: 0.56
  stage: growing
  synapse_in: 20
  synapse_out: 12
---
## Definition

Troubleshooting MCP (Model Context Protocol) infrastructure covers the diagnostic procedures for identifying and resolving failures in the MCP server stack that supports the Cohezion vault. MCP servers provide programmatic access to vault content, embeddings, and external services; when they fail, agents lose the ability to query knowledge, generate embeddings, or sync data. Common failure modes include server crashes, port conflicts, authentication errors, timeout issues, and telemetry corruption.

The troubleshooting approach follows a layered strategy: check connectivity first, then authentication, then service health, then data integrity.

## Key Properties

- **Port verification**: Confirm MCP servers are listening on expected ports (Cloud Vault MCP on 8360, Ollama on 11434).
- **Log inspection**: Check server logs for error traces; watch for debug log bloat that can fill disk (see [[2026-02-10-debug-log-bloat-analysis]]).
- **Health endpoints**: Use `/health` or equivalent endpoints to verify server responsiveness before debugging deeper.
- **Telemetry integrity**: Corrupted telemetry data can cause cascading failures; verify data formats match expected schemas.
- **Dependency chain**: MCP servers depend on upstream services (Ollama, SurrealDB); failures often originate upstream.

## Diagnostic Steps

1. **Check process status**: `ps aux | grep mcp` or `systemctl status <service>`
2. **Test connectivity**: `curl http://127.0.0.1:8360/health`
3. **Check logs**: Look for recent errors in server log output
4. **Verify auth**: Confirm bearer tokens in `mcp.json` match server expectations
5. **Test upstream**: Verify Ollama (`curl http://localhost:11434/api/version`) and SurrealDB are reachable
6. **Restart and monitor**: Restart the failing service and watch logs for startup errors

## Related Papers

- [[2026-02-10-debug-log-bloat-analysis]]
- [[2026-02-10-phase-a-implementation-complete]]
- [[2026-02-10-telemetry-corruption-fix]]
- [[log-rotation-and-monitoring]]
- [[mcp-infrastructure-architecture]]
- [[runbook-benchmarking-validation]]
- [[runbook-ci-cd-pipeline]]
- [[runbook-health-checks]]
- [[runbook-ollama-mcp-operations]]

## Related Concepts

- [[mcp-model-context-protocol]] -- the protocol standard that MCP servers implement
- [[runbook-health-checks]] -- proactive health monitoring that prevents troubleshooting scenarios
- [[runbook-ollama-mcp-operations]] -- Ollama-specific operational procedures
- [[cloud-vault-mcp]] -- the primary MCP server for this vault
- [[2026-02-09-session-43-mcp-setup|Session 43: MCP Setup]] — the FastMCP Mount bug found in this session is a canonical MCP infrastructure troubleshooting case
- [[cerebellum/troubleshooting-mcp-infrastructure|Troubleshooting Guide (Operational)]] -- full diagnostic runbook: Ollama MCP restart, CI failure patterns, health check timeouts, benchmark slowdowns, API hangs

## Relevance to Cohezion

MCP infrastructure is the bridge between the Cohezion vault and the agents that consume it. When MCP servers are down, agents fall back to file-based search (slower, less semantic) or lose vault access entirely. This troubleshooting guide ensures operators can restore service quickly, minimizing the window during which agents operate without their knowledge base.
