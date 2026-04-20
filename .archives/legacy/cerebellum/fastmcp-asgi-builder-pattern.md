---
title: FastMCP ASGI Builder Pattern
date: 2026-02-09
domain: mcp-integration
tags: [asgi, fastmcp, python, server-framework, builder-pattern]
aspect: thinker
neural:
  activation: 0.67
  stage: growing
  synapse_in: 5
  synapse_out: 4
---

# Pattern: FastMCP ASGI Builder Pattern

## Problem
How do you integrate FastMCP with ASGI servers (uvicorn, Starlette)?

FastMCP is not a callable ASGI application by itself—it's a builder/configurator. Trying to use it directly causes `TypeError: 'FastMCP' object is not callable`.

## Solution
FastMCP uses a **builder pattern** with **factory methods**. Configure tools via decorators, then call a factory method to generate the actual ASGI app.

### Three-Step Pattern

```python
from mcp.server.fastmcp import FastMCP
import uvicorn

# Step 1: Create the configurator/builder
mcp = FastMCP("My Server")

# Step 2: Configure via decorators (decorators register, don't build)
@mcp.tool()
def my_tool(arg: str) -> str:
    """A tool that does something."""
    return f"Result: {arg}"

# Step 3: Build the actual ASGI app via factory method
app = mcp.streamable_http_app()

# Step 4: Run the ASGI app with uvicorn
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

## Common Pitfall

```python
# ❌ BROKEN: FastMCP instance is not callable
mcp = FastMCP("server")
uvicorn.run(mcp)  # TypeError: 'FastMCP' object is not callable
```

**Fix**: Call a factory method to get the ASGI app:
```python
# ✅ CORRECT: Call factory method
mcp = FastMCP("server")
app = mcp.streamable_http_app()
uvicorn.run(app)
```

## Factory Methods

FastMCP provides two factory methods for different transport modes:

### 1. `streamable_http_app()` - HTTP/HTTPS Request/Response
- Returns: `Starlette` ASGI application
- Transport: HTTP/HTTPS (stateless request/response)
- Best for: Tool execution via HTTP, Claude Code integration
- Supports: Both stateful and streaming contexts

**Use case**: Claude Code using `~/.claude/mcp.json` with `"type": "http"`

```python
app = mcp.streamable_http_app()
uvicorn.run(app, host="0.0.0.0", port=8000)
```

### 2. `sse_app()` - Server-Sent Events
- Returns: `Starlette` ASGI application
- Transport: HTTP with event streaming (SSE)
- Best for: Real-time event streaming, observability
- Supports: Long-lived connections

**Use case**: Real-time vault file watcher events, metrics streams

```python
app = mcp.sse_app()
uvicorn.run(app, host="0.0.0.0", port=8000)
```

## Hybrid Routing Example

For Vault MCP, we use **hybrid routing**: SSE for watcher events, HTTP/MCP for tool calls.

```python
from starlette.applications import Starlette
from starlette.routing import Mount, Route

# Create both apps
mcp_app = mcp.streamable_http_app()
sse_app = SSE_stream.sse_endpoint

# Create router that directs traffic
async def router_app(scope, receive, send):
    if scope["path"] == "/events/vault":
        # Real-time vault events → SSE
        await sse_app(scope, receive, send)
    else:
        # Tool calls → FastMCP HTTP
        await mcp_app(scope, receive, send)

uvicorn.run(router_app, host="0.0.0.0", port=8000)
```

## Design Pattern: Builder vs. Instance

FastMCP uses the **Builder Pattern**:
- **Builder role**: `FastMCP()` instance configures tools (via decorators)
- **Product role**: `app` from factory method is the actual ASGI application
- **Separation**: Configuration (builder) is separate from execution (app)

This enables:
- ✅ Clean API (decorators look like direct registration)
- ✅ Lazy initialization (ASGI app built when needed)
- ✅ Multiple factory methods (different transports)
- ✅ Extensibility (custom factory methods possible)

## Integration with Middleware

FastMCP apps work with Starlette middleware:

```python
from starlette.middleware.trustedhost import TrustedHostMiddleware

mcp_app = mcp.streamable_http_app()

# Wrap with middleware
app = TrustedHostMiddleware(mcp_app, allowed_hosts=["localhost", "127.0.0.1"])

uvicorn.run(app, host="0.0.0.0", port=8000)
```

## Real-World Example: Cloud Vault MCP

**File**: `cloud-vault-mcp/src/mcp_server/main.py`

```python
def main():
    # 1. Create FastMCP configurator
    mcp = create_server(config)

    # 2. Build ASGI app
    mcp_app = mcp.streamable_http_app()

    # 3. Optionally wrap with middleware
    if "*" not in config.allowed_hosts:
        mcp_app = TrustedHostMiddleware(mcp_app, allowed_hosts=config.allowed_hosts)

    # 4. For watcher mode, set up hybrid routing
    if config.watcher_enabled:
        async def app(scope, receive, send):
            if scope["path"] == "/events/vault":
                await sse_app(scope, receive, send)
            else:
                await mcp_app(scope, receive, send)
    else:
        app = mcp_app

    # 5. Run with uvicorn
    uvicorn.run(app, host=config.host, port=config.port)
```

## Key Takeaways

| Aspect | Details |
|--------|---------|
| **Pattern** | Builder Pattern (configurator + factory methods) |
| **Pitfall** | Using `FastMCP` instance directly as ASGI app |
| **Fix** | Call `.streamable_http_app()` or `.sse_app()` |
| **HTTP Transport** | Use `streamable_http_app()` (for Claude Code) |
| **Streaming Transport** | Use `sse_app()` (for real-time events) |
| **Middleware** | Compatible with Starlette middleware |
| **Configuration** | Done via decorators on builder instance |
| **Execution** | Happens in ASGI app from factory method |

## See Also

- [[2026-02-09-fastmcp-asgi-integration-fix|Decision: FastMCP ASGI Integration Fix]] - Bug fix decision log
- [[2026-02-09-session-43-mcp-setup|Decision: Session 43 MCP Server Setup & Obsidian Integration]] - Context where bug was first identified
- FastMCP documentation: https://modelcontextprotocol.io
- Starlette ASGI app docs: https://www.starlette.io/

[[mcp-infrastructure-architecture]], [[mcp-model-context-protocol]]