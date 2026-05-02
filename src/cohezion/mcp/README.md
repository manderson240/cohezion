# Cohezion MCP Server Framework

This directory contains Model Context Protocol (MCP) servers and the fleet management infrastructure.

## MCP Server Reliability Checklist

When implementing or updating an MCP server, ensure the following best practices are followed to prevent regressions and common API pitfalls:

### 1. API Response Hardening
- **Always handle optional fields**: Use `.get("field", default)` or Pydantic models for parsing JSON responses.
- **Type verification**: Never assume a field's type (e.g., labels can be strings or dictionaries).
- **Graceful degradation**: Return empty lists or meaningful error dictionaries instead of letting exceptions bubble up to the MCP transport layer.

### 2. Filtering and Scope
- **Implicit vs. Explicit results**: Some APIs (like GitHub `/issues`) return mixed results (Issues + PRs). Always filter to the expected scope.
- **Limit enforcement**: Respect upstream API boundaries (e.g., GitHub's 100 per page limit) and the user-provided `limit`.

### 3. Testing
- **Mandatory Mocks**: Every server MUST have a unit test in `tests/mcp/` using `unittest.mock` to simulate upstream API responses.
- **Edge cases**: Test empty responses, malformed JSON, and maximum pagination limits.

### 4. Lifecycle & Performance
- **Lazy Initialization**: Initialize slow resources (clients, vaults) only when needed, not at module import time.
- **Session Management**: Use a single `aiohttp.ClientSession` where possible and ensure it is closed properly on shutdown.

## Hook Lifecycle Support

Cohezion supports a robust hook system via **Hookify** and the **Sandbox Hook Engine**. 

### Pre-Tool Hooks (Validation & Safety)
- **Purpose**: Validate arguments, check HIHO coherence, or enforce security policies BEFORE a tool runs.
- **Trigger**: `pre_execute` or `mcp_pre_execute`.
- **Implementation**: Call `hookify_validate` via the Hookify MCP server.

### Post-Tool Hooks (Audit & Learning)
- **Purpose**: Log outcomes, update the knowledge graph, or trigger recursive refinement AFTER a tool runs.
- **Trigger**: `post_execute` or `mcp_post_execute`.
- **Implementation**: Persist results to the SurrealDB graph or Obsidian vault.

## Adding a New Server
1. Create your server in `src/cohezion/mcp/servers/<name>/`.
2. Register it in `src/cohezion/mcp/mcp_registry.json`.
3. Add tests in `tests/mcp/test_<name>_server.py`.
4. Verify with `uv run pytest tests/mcp/`.
