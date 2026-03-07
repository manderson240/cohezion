# Adding New MCP Servers

This guide shows you how to add any new MCP server to your infrastructure in **~30 minutes**.

## Quick Start

```python
# 1. Copy the template
cp src/cohezion/mcp/servers/template/server.py \
   src/cohezion/mcp/servers/my_service/server.py

# 2. Customize the service class
# 3. Add your tools
# 4. Register with MCP Manager
# 5. Done!
```

---

## Step-by-Step: Add a New Server

### Step 1: Create Server File (5 min)

Create a new file in `src/cohezion/mcp/servers/{service_name}/server.py`:

```python
"""My Custom Service MCP Server."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
from typing import Any

from aiohttp import web

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)

MCP_PORT = int(os.getenv("MCP_PORT", "8363"))


class MyService:
    """Your service implementation."""
    
    async def do_something(self, param: str) -> dict:
        """Your service method."""
        return {"result": f"Processed: {param}"}


_service: MyService | None = None

def get_service() -> MyService:
    global _service
    if _service is None:
        _service = MyService()
    return _service


routes = web.RouteTableDef()


@routes.get("/health")
async def health(request: web.Request) -> web.Response:
    """Health check - REQUIRED."""
    return web.json_response({
        "status": "healthy",
        "server": "my_service",
        "port": MCP_PORT,
    })


@routes.post("/tools/my_service_do_something")
async def tool_do_something(request: web.Request) -> web.Response:
    """Your tool endpoint."""
    try:
        data = await request.json()
        param = data.get("param", "")
        
        service = get_service()
        result = await service.do_something(param)
        
        return web.json_response({
            "tool": "my_service_do_something",
            "result": result,
        })
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


async def main():
    app = web.Application()
    app.add_routes(routes)
    
    logger.info(f"Starting My Service MCP Server on port {MCP_PORT}")
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", MCP_PORT)
    await site.start()
    
    while True:
        await asyncio.sleep(3600)


if __name__ == "__main__":
    asyncio.run(main())
```

---

### Step 2: Register with MCP Manager (2 min)

Add to `src/cohezion/mcp/manager/server_manager.py`:

```python
def init_default_servers():
    manager = get_manager()
    
    # Existing servers...
    manager.register_server(
        name="bmad",
        entry_point="cohezion.mcp.servers.bmad.server:app",
        preferred_port=8361,
    )
    
    manager.register_server(
        name="skills",
        entry_point="cohezion.mcp.servers.skills.server:app", 
        preferred_port=8362,
    )
    
    # NEW SERVER - Add this:
    manager.register_server(
        name="my_service",  # Unique name
        entry_point="cohezion.mcp.servers.my_service.server:app",
        preferred_port=8363,  # Next available port
        auto_restart=True,
        env_vars={
            "MY_SERVICE_API_KEY": os.getenv("MY_SERVICE_API_KEY", ""),
        },
    )
```

---

### Step 3: Add to Docker Compose (5 min)

Add to `docker-compose.mcp.yml`:

```yaml
services:
  # Existing services...
  
  my-service-mcp:  # NEW SERVICE
    build:
      context: .
      dockerfile: Dockerfile.my-service  # Or reuse existing
    container_name: my-service-mcp
    ports:
      - "8363:8363"
    environment:
      - MCP_PORT=8363
      - REDIS_URL=redis://redis-mcp:6379
      - MY_SERVICE_API_KEY=${MY_SERVICE_API_KEY}
    volumes:
      - ./src/cohezion/mcp/servers/my_service:/app/mcp/my_service:ro
    depends_on:
      redis-mcp:
        condition: service_healthy
    restart: unless-stopped
    networks:
      - mcp-network
```

---

### Step 4: Platform Integration (10 min)

Add MCP config for opencode (`.opencode/mcp.json`):

```json
{
  "mcpServers": {
    "bmad": { ... },
    "skills": { ... },
    "my_service": {
      "name": "My Service",
      "type": "streamable-http",
      "url": "http://localhost:8363",
      "port": 8363,
      "description": "My custom service via MCP"
    }
  }
}
```

Add native command (`.opencode/commands/my-service-do-something.md`):

```markdown
---
name: my-service-do-something
description: Do something with my service
---

# My Service - Do Something

Use the my_service_do_something tool via MCP.

## Usage

The tool accepts:
- `param`: Parameter to process

## Example

```python
# Tool will be called via MCP
# Result returned as JSON
```
```

---

### Step 5: Test (5 min)

```bash
# Start the new server
python3 -m cohezion.mcp.servers.my_service.server

# Test health
curl http://localhost:8363/health

# Test tool
curl -X POST http://localhost:8363/tools/my_service_do_something \
  -H "Content-Type: application/json" \
  -d '{"param": "hello"}'
```

---

## Available Port Range

| Port | Server | Status |
|------|--------|--------|
| 8360 | Cloud Vault MCP | Reserved |
| 8361 | BMAD MCP | ✅ Active |
| 8362 | Skills.sh MCP | ✅ Active |
| 8363 | **Available** | 🔓 Ready |
| 8364 | **Available** | 🔓 Ready |
| ... | ... | ... |
| 8399 | **Available** | 🔓 Ready |

**40 ports available** (8360-8399)

---

## Example: GitHub MCP Server

Here's a complete example of a GitHub MCP server:

```python
"""GitHub MCP Server - Access GitHub API via MCP."""

import os
import aiohttp
from aiohttp import web

MCP_PORT = int(os.getenv("MCP_PORT", "8363"))
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")

routes = web.RouteTableDef()


@routes.get("/health")
async def health(request: web.Request):
    return web.json_response({"status": "healthy", "server": "github"})


@routes.post("/tools/github_search_repos")
async def search_repos(request: web.Request):
    data = await request.json()
    query = data.get("query", "")
    
    async with aiohttp.ClientSession() as session:
        headers = {"Authorization": f"token {GITHUB_TOKEN}"}
        url = f"https://api.github.com/search/repositories?q={query}"
        
        async with session.get(url, headers=headers) as resp:
            result = await resp.json()
            return web.json_response({
                "tool": "github_search_repos",
                "count": result.get("total_count", 0),
                "repositories": result.get("items", [])[:10]
            })


@routes.post("/tools/github_get_repo")
async def get_repo(request: web.Request):
    data = await request.json()
    owner = data.get("owner")
    repo = data.get("repo")
    
    async with aiohttp.ClientSession() as session:
        headers = {"Authorization": f"token {GITHUB_TOKEN}"}
        url = f"https://api.github.com/repos/{owner}/{repo}"
        
        async with session.get(url, headers=headers) as resp:
            result = await resp.json()
            return web.json_response({
                "tool": "github_get_repo",
                "name": result.get("name"),
                "stars": result.get("stargazers_count"),
                "language": result.get("language"),
                "url": result.get("html_url")
            })


@routes.post("/tools/github_create_issue")
async def create_issue(request: web.Request):
    data = await request.json()
    owner = data.get("owner")
    repo = data.get("repo")
    title = data.get("title")
    body = data.get("body", "")
    
    async with aiohttp.ClientSession() as session:
        headers = {
            "Authorization": f"token {GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+json"
        }
        url = f"https://api.github.com/repos/{owner}/{repo}/issues"
        payload = {"title": title, "body": body}
        
        async with session.post(url, headers=headers, json=payload) as resp:
            result = await resp.json()
            return web.json_response({
                "tool": "github_create_issue",
                "issue_number": result.get("number"),
                "url": result.get("html_url"),
                "status": "created"
            })


# ... main() function
```

**Time to implement**: 25 minutes

---

## Example: Database MCP Server

```python
"""PostgreSQL MCP Server - Query databases via MCP."""

import asyncpg
from aiohttp import web

MCP_PORT = int(os.getenv("MCP_PORT", "8364"))
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://localhost/mydb")

routes = web.RouteTableDef()

_pool: asyncpg.Pool | None = None

async def get_pool():
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(DATABASE_URL)
    return _pool


@routes.get("/health")
async def health(request: web.Request):
    return web.json_response({"status": "healthy", "server": "postgres"})


@routes.post("/tools/postgres_query")
async def query_database(request: web.Request):
    data = await request.json()
    sql = data.get("sql", "")
    params = data.get("params", [])
    
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(sql, *params)
            return web.json_response({
                "tool": "postgres_query",
                "row_count": len(rows),
                "rows": [dict(row) for row in rows[:100]]
            })
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


@routes.post("/tools/postgres_tables")
async def list_tables(request: web.Request):
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT table_name FROM information_schema.tables WHERE table_schema='public'"
        )
        return web.json_response({
            "tool": "postgres_tables",
            "tables": [row["table_name"] for row in rows]
        })
```

---

## Server Manager API

Once registered, manage servers via HTTP:

```bash
# Get all servers status
curl http://localhost:8370/

# Start specific server
curl -X POST http://localhost:8370/servers/my_service/start

# Stop server
curl -X POST http://localhost:8370/servers/my_service/stop

# Restart server
curl -X POST http://localhost:8370/servers/my_service/restart

# Check health
curl http://localhost:8370/servers/my_service/health
```

---

## Best Practices

### 1. Health Check (Required)
Every server MUST have a `/health` endpoint:

```python
@routes.get("/health")
async def health(request: web.Request):
    return web.json_response({
        "status": "healthy",
        "server": "your_service",
        "port": MCP_PORT
    })
```

### 2. Error Handling
Always return proper error responses:

```python
@routes.post("/tools/your_tool")
async def your_tool(request: web.Request):
    try:
        # ... do work
        return web.json_response({"result": result})
    except Exception as e:
        logger.exception("Tool failed")
        return web.json_response(
            {"error": str(e)}, 
            status=500
        )
```

### 3. Environment Variables
Use env vars for configuration:

```python
MCP_PORT = int(os.getenv("MCP_PORT", "8363"))
API_KEY = os.getenv("MY_SERVICE_API_KEY", "")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
```

### 4. Logging
Use structured logging:

```python
logger.info(f"Starting {SERVICE_NAME} server on port {MCP_PORT}")
logger.debug(f"Cache hit for {skill_id}")
logger.error(f"Failed to fetch skill: {e}")
```

### 5. Async Patterns
Use async/await throughout:

```python
# Good
async def get_data():
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            return await resp.json()

# Bad (blocking)
def get_data():
    return requests.get(url).json()  # Don't do this!
```

---

## Common Services to Add

| Service | Port | Time | Use Case |
|---------|------|------|----------|
| **GitHub** | 8363 | 25 min | Repo management |
| **Slack** | 8364 | 20 min | Notifications |
| **Stripe** | 8365 | 30 min | Payments |
| **PostgreSQL** | 8366 | 20 min | Database queries |
| **AWS** | 8367 | 40 min | Cloud operations |
| **Docker** | 8368 | 25 min | Container management |
| **Kubernetes** | 8369 | 35 min | K8s operations |
| **Jira** | 8370 | 25 min | Issue tracking |

---

## Troubleshooting

### Port Already in Use

```bash
# Find process using port
lsof -i :8363

# Kill it
kill -9 <PID>

# Or use auto-allocation (let MCP Manager pick port)
manager.register_server(
    name="my_service",
    entry_point="...",
    # Don't specify preferred_port, let it auto-allocate
)
```

### Server Won't Start

Check logs:
```bash
# View logs
tail -f cloud-vault-mcp/vault/logs/my_service.log

# Or Docker logs
docker logs my-service-mcp
```

### Health Check Fails

Ensure your health endpoint returns 200:
```bash
curl -v http://localhost:8363/health
```

---

## Summary

Adding a new MCP server:
1. ✅ Copy template (5 min)
2. ✅ Implement your service (15 min)
3. ✅ Register with manager (2 min)
4. ✅ Add to Docker Compose (5 min)
5. ✅ Test (5 min)

**Total: ~30 minutes per server**

---

**Your infrastructure can now host 40 MCP servers on ports 8360-8399!**
