---
title: Cloud Vault MCP
date: 2026-02-23
tags: [project, mcp, infrastructure, compound-engineering, tool-use]
related_concepts: [mcp-model-context-protocol, mcp-infrastructure-architecture, surrealdb, compound-engineering, tool-use]
status: active
aspect: knower
neural:
  activation: 1.0
  stage: mature
  synapse_in: 0
  synapse_out: 39
---

# Cloud Vault MCP

The Cloud Vault MCP server is Cohezion's primary knowledge management and agent infrastructure interface, implemented as an HTTP [[mcp-model-context-protocol]] server running on port 8360. It exposes 30+ tools across six categories, providing AI agents with programmatic access to the Obsidian vault, SurrealDB graph database, Google Sheets, Ollama inference, and Teleport task management — all through a single standardized protocol.

The server implements three logical operation layers. **VaultOps** handles file-level vault operations: reading, writing, searching, and cross-linking notes. **CompoundOps** implements the compound engineering primitives: `vault_log_decision`, `vault_log_experiment`, `vault_extract_pattern`, and `vault_find_relevant_context` — the tools that make the [[experience-feedback-loop]] concrete. **ObsidianOps** manages the graph layer: backlinks, forward links, tags, and wiki-link validation. Together these layers turn the Obsidian vault from a passive note store into an active, queryable knowledge graph that agents can read from and write to during execution.

The server was built using FastMCP (Python) and serves as the reference template for additional MCP servers in the Cohezion ecosystem. The `cloud-vault-mcp/` directory is explicitly documented as the template to copy when building new MCP servers, carrying 87% token savings versus building from scratch. It runs alongside the Ollama MCP server (stdio, no port) and exposes a `/health` endpoint that monitors all five infrastructure dependencies.

## Navigation

- [[MOC-platform-infrastructure]] — Map of Content for platform infrastructure including MCP, SurrealDB, and CI/CD

## Related
- [[mcp-infrastructure-architecture]]
- [[surrealdb]]
- [[surrealdb-graph-databases]] — the SurrealDB graph database is the agent context graph backend for this MCP server
- [[anthropic-mcp-apps-claude-integrations]] — demonstrates the broader MCP ecosystem this server participates in
- [[kyutai-mcp-server-architecture|Kyutai MCP Server Architecture]] — a companion MCP server (port 8361) built using this server's FastMCP patterns as a template
- [[kyutai-api-specification|Kyutai API Specification]] — the Kyutai voice AI APIs served by the companion Kyutai MCP server
- [[google-sheets-vault-integration]] — the project that integrates Google Sheets into this MCP server via the SheetsBridge tool category (sheets_bridge.py)
- [[2026-02-11-vault-first-knowledge-architecture|Vault-First Knowledge Architecture]] — the decision establishing the vault as source of truth, which this MCP server provides programmatic access to
- [[2026-02-12-cloudflare-tunnel-for-persistent-mcp-remote-access|Cloudflare Tunnel for MCP Remote Access]] — exposes this MCP server remotely via persistent Cloudflare tunnel

- [[Autonomous-Context-Hooks-Guide]] — autonomous hooks that use this MCP server's vault search and write tools to auto-load context before agent prompts

- [[kyutai-project]] — the Kyutai research initiative that originally inspired the MCP server naming and architecture
- [[2026-02-09-session-43-mcp-setup|Session 43: MCP Setup]] — the MCP server infrastructure initialized in this session on port 8360
- [[local-agent-orchestration-roadmap]] — the orchestration roadmap that depends on this MCP server for vault access in the local agent swarm
- [[vault-knowledge-graph-densification]] — graph densification project that enriches the data this MCP server serves to agents
- [[2026-02-10-kyutai-mcp-obsidian-plugin-plan]] — the original plugin plan that defined the MCP server's tool categories
- [[2026-02-09-ollama-mcp-server]] — the companion Ollama MCP server that handles embedding and inference alongside this vault server
- [[2026-02-14-settings-files-validation-and-fix]] — settings validation that ensures MCP server configuration integrity

## Missions

- [[research-pipeline-2026-02-26]] — Vault write and sheets bridge operations used for 900-row research pipeline output

## Specs & Projects

- [[cloud-vault-mcp|Cloud Vault MCP Spec]] — Full server spec with tools catalog, env vars, and reconstruction instructions (in `specs/mcp-servers/`)
- [[2026-03-05-vault-surrealdb-sync-pipeline]] — PRD for real-time vault↔SurrealDB sync via this server
- [[2026-03-05-vault-surrealdb-architecture]] — Architecture ADR for the three-layer sync pattern
- [[ide-and-model-providers]] — IDE and model provider integration points for connecting to this server

## Cards

- [[cloud-vault-mcp|System Card: Cloud Vault MCP]] — System card in `specs/systems/`
- [[surrealdb|System Card: SurrealDB 3.0]] — System card for the graph database backend
- [[ollama|System Card: Ollama]] — System card for the embedding/inference server

## Benchmarks

- [[release-metrics]] — Kyutai v0.1.0-alpha performance release metrics: 36.75MB baseline memory, 537 req/60s throughput

## Related Lessons

- [[lesson-05-surrealdb]] — SurrealDB query patterns and syntax gotchas; critical knowledge for the SurrealDB tools in this server
- [[lesson-36-mcp-configuration-requires-end-to-end-test-new]] — MCP servers must be tested end-to-end with a real client connection; unit tests miss protocol negotiation failures
- [[lesson-surrealdb-schema-design]] — record-centric SurrealDB schema design outperforms table-centric for agent context graphs

## Daily References

- [[SESSION-61-COMPLETE-SUMMARY]]
- [[SESSION-60-COMPLETION-SUMMARY]]
- [[SESSION-57-COMPLETION-SUMMARY]]
- [[SESSION-2026-02-10-WORK-SUMMARY]]
- [[2026-03-04-anthropic-portfolio-night-session]]
- [[2026-02-14-wave-1-delivery-complete]]
- [[2026-02-10-ollama-mcp-implementation]] — Ollama MCP server Phase 1 implementation: 80/80 tests passing, 1200+ lines across 6 modules
- [[2026-02-09-sheetsbridge-test-plan]] — SheetsBridge end-to-end test plan for live Google Sheet integration
- [[2026-02-09-sheetsbridge-verified]] — SheetsBridge MCP integration verified: 17/17 tests passed

## Skills

- OBSIDIAN_MCP_INTEGRATION_PRIME — AI agent vault access via MCP
- OBSIDIAN_VAULT_INTEGRATION_PRIME — Obsidian vault integration for agents
