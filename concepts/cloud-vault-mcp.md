---
title: Cloud Vault MCP
date: 2026-02-23
tags: [project, mcp, infrastructure]
status: stub
---

# Cloud Vault MCP

The cloud-vault-mcp server — HTTP MCP server on port 8360 providing programmatic access to the Cohezion vault. Implements VaultOps, CompoundOps, ObsidianOps, Teleport, SheetsBridge, and SurrealDB tools.

## Related
- [[mcp-infrastructure-architecture]]
- [[surrealdb]]
- [[surrealdb-graph-databases]] — the SurrealDB graph database is the agent context graph backend for this MCP server
- [[anthropic-mcp-apps-claude-integrations]] — demonstrates the broader MCP ecosystem this server participates in
- [[research/kyutai-mcp-server-architecture|Kyutai MCP Server Architecture]] — a companion MCP server (port 8361) built using this server's FastMCP patterns as a template
- [[research/kyutai-api-specification|Kyutai API Specification]] — the Kyutai voice AI APIs served by the companion Kyutai MCP server
