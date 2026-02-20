---
date: 2026-02-09
project: cloud-vault-mcp
status: implemented
tags: [mcp, asgi, bugfix, integration]
---

# Decision: Use FastMCP.streamable_http_app() for ASGI Integration

## Context
The Cloud Vault MCP server was crashing on HTTP requests with `TypeError: 'FastMCP' object is not callable`. This prevented Claude Code from accessing vault tools and blocked compound engineering workflows.

## Problem
FastMCP is a builder/configurator pattern, not a callable ASGI application. The instance configures tools via decorators, but must call a factory method to generate the actual Starlette ASGI application.

**Root Cause** (main.py:50):
```python
# BROKEN: FastMCP is not callable
mcp_app = mcp
uvicorn.run(mcp_app)  # TypeError at runtime
```

## Solution
Use `FastMCP.streamable_http_app()` factory method to get a callable Starlette application.

**Implementation** (main.py:50):
```python
# FIXED: Call factory method to get ASGI app
mcp_app = mcp.streamable_http_app()
uvicorn.run(mcp_app)  # ✅ Works
```

## Rationale
- **Claude Code transport**: Claude Code uses HTTP transport (configured in `~/.claude/mcp.json` as `"type": "http"`)
- **StreamableHTTP benefits**: Supports both stateless request/response and stateful streaming modes, compatible with tool execution patterns
- **Alternative considered**: SSE (Server-Sent Events) for real-time streaming—but already handled via separate `/events/vault` route for watcher mode
- **Minimal change**: Single-line fix, zero impact on existing APIs

## Consequences

### Benefits
✅ MCP server starts successfully without TypeError
✅ HTTP tool calls from Claude Code work properly
✅ Vault tool discovery and execution enabled
✅ Both watcher-enabled and watcher-disabled modes functional
✅ No breaking changes to existing APIs

### Testing
- **Watcher disabled**: ✅ Server starts, HTTP 404 on root (expected), application startup complete
- **Watcher enabled**: ✅ Server starts, VaultFileWatcher running, both HTTP and SSE routes functional
- **Tool execution**: ✅ Multiple vault operations tested (vault_list, vault_read, vault_search)
- **Stability**: ✅ Server runs for 1+ hour without crashes

## Edge Cases Handled
- Hybrid routing (watcher mode): SSE → `/events/vault`, MCP → all other routes ✅
- Graceful startup: VaultFileWatcher initialization during lifespan ✅
- TLS/HTTPS integration: Works with both `streamable_http_app()` and HTTPS middleware ✅

## Pattern: FastMCP Builder Pattern
FastMCP uses a builder/configurator pattern common in modern Python libraries:

```python
# Step 1: Create builder/configurator
builder = FastMCP("My Server")

# Step 2: Configure via decorators (non-mutating)
@builder.tool()
def my_tool():
    return "result"

# Step 3: Build the actual ASGI app (factory method)
app = builder.streamable_http_app()

# Step 4: Run the ASGI app
uvicorn.run(app)
```

**Factory methods available**:
- `streamable_http_app()` - HTTP/HTTPS request/response transport
- `sse_app()` - Server-Sent Events streaming transport

## Impact on Vault Integration
This fix enables the full MCP ↔ Vault integration chain:
- Claude Code discovers vault tools via MCP server ✅
- Tool calls route through StreamableHTTP to FastMCP ✅
- FastMCP dispatches to vault_ops (read, write, search, link) ✅
- Compound executor can access vault for skill selection, pattern extraction, experience-guided routing ✅

## Deployment Notes
- Change is backward compatible (no API changes)
- No configuration changes required
- Existing Claude Code MCP config continues to work
- Optional: Update TROUBLESHOOTING.md with FastMCP builder pattern explanation

## Related
**Domains**: infrastructure, integration
**Categories**: operational, technical


[[mcp-infrastructure-architecture]], [[mcp-model-context-protocol]]

## Relevance to Cohezion

[[MCP Infrastructure Architecture]]

## Related Concepts

- [[2026-02-10-kyutai-mcp-obsidian-plugin-plan]]
- [[2026-02-09-ollama-mcp-server]]
- [[2026-02-14-settings-files-validation-and-fix]]
- [[2026-02-14-graphrag-verification-and-integration-session]]
- [[entire-io-to-vault-mapping]]
- [[sheetsbr idge-mcp-testing]]
- [[fastmcp-asgi-builder-pattern]]
- [[google-sheets-vault-bridge]]
