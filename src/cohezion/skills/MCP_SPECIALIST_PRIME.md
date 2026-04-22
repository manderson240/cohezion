---
name: mcp-specialist-prime
description: "Expert in MCP (Model Context Protocol) server design, tool schemas, FastMCP patterns, health monitoring, and inter-server coordination. Manages the tool layer that connects all Cohezion agents to their capabilities."
---

# SKILL: MCP_SPECIALIST_PRIME

## DOMAIN EXPERTISE
Expert in **MCP (Model Context Protocol) server design, tool schemas, FastMCP patterns, health monitoring, and inter-server coordination**. Manages the tool layer that connects all Cohezion agents to their capabilities.

## KEY CONCEPTS
- **MCP**: Industry-standard protocol for agent ↔ tool connectivity (97M downloads, Linux Foundation stewardship).
- **FastMCP**: Python framework for building MCP servers. `@mcp.tool()` decorator + typed params + docstrings.
- **Server fleet**: cloud-vault-mcp (41+ tools, port 8360), cohezion-compound (stdio), bmad (8361), cohezion-maintenance-mcp (8362).
- **Permissions**: `.claude/settings.local.json` `allowedTools` array. Format: `mcp__server-name__tool_name`.
- **Health hook**: `.claude/hooks/mcp-health-check.sh` pings servers at session start.

## INSTRUCTION

1. **New tool design**: Use `@mcp.tool()` with explicit type annotations and clear docstrings. Return JSON strings. Graceful error fallback (never crash, return `{"error": "..."}` instead).
2. **Server scaffolding**: Copy `cloud-vault-mcp/` as template. Set unique port. Add entry point in `pyproject.toml`.
3. **Permission registration**: After adding tools, update `.claude/settings.local.json` with `mcp__server__tool` entries.
4. **Health monitoring**: Each server should respond to health pings. Use `httpx` for async checks.
5. **Inter-server flow**: vault-mcp writes data → maintenance-mcp checks health → compound-mcp uses guidance.

## PATTERNS
- Stateless HTTP mode for multi-client MCP servers (`stateless_http=True`)
- Async/await for all I/O (SurrealDB queries, vault file access)
- Graceful degradation: if SurrealDB is down, return empty results with error message
- Config via environment variables: `SURREAL_URL`, `VAULT_PATH`, etc.

## ANTI-PATTERNS
- Sync blocking calls inside MCP tool handlers (freezes the server)
- Hardcoded paths (use `os.environ` + `Path.expanduser`)
- Missing error handling (one bad query crashes the entire server)
- Adding tools without updating settings.local.json permissions

## VERSION
v1.0

## SEE ALSO
cloud-vault-mcp/ (proven template), cohezion-maintenance-mcp/ (graph health)
