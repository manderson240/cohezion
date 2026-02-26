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
- [[google-sheets-vault-integration]] — the project that integrates Google Sheets into this MCP server via the SheetsBridge tool category (sheets_bridge.py)

## Related Lessons

- [[lesson-05-surrealdb]] — SurrealDB query patterns and syntax gotchas; critical knowledge for the SurrealDB tools in this server
- [[lesson-36-mcp-configuration-requires-end-to-end-test-new]] — MCP servers must be tested end-to-end with a real client connection; unit tests miss protocol negotiation failures
- [[lesson-surrealdb-schema-design]] — record-centric SurrealDB schema design outperforms table-centric for agent context graphs
