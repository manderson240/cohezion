---
name: cohezion-mcp-servers
description: |
  Call Cohezion's custom HTTP MCP servers (ports 8361-8381). Use when: (1) a user
  mentions MCP servers are running, (2) you see port numbers 836x/838x, (3) you need
  BMAD workflows, Memory, Git context, Sequential thinking, Security scanning, or
  the Skills.sh registry. These servers use /tools/<name> REST endpoints, NOT standard
  MCP JSON-RPC. SurrealDB runs on port 8000 but may be in read-only mode.
author: Claude Code
version: 1.0.0
---

# Cohezion MCP Servers

## Server Inventory

| Port | Name | Key Tools |
|------|------|-----------|
| 8361 | BMAD | 607 workflows, 28 agents |
| 8362 | Skills.sh | Skills registry cache |
| 8364 | Doc Retriever | (SSE/websocket — not REST) |
| 8366 | Memory | ERO model: entities, relations, observations |
| 8367 | Sequential | Thinking chains with branching |
| 8368 | Git Context | git_status, git_diff, git_log, git_branches, git_info |
| 8369 | Security | OWASP scan, security checklist |
| 8365 | (Unknown) | Detected in ss output, not in status table |
| 8380 | Plasma Physics | (not REST) |
| 8381 | Report Generation | (not REST) |
| 8000 | SurrealDB | Direct HTTP SQL (may be read-only) |

## Transport: REST at `/tools/<name>`

**These servers do NOT use standard MCP JSON-RPC.** They use plain HTTP POST with JSON body.

### Discovery Workflow

```bash
# 1. Check which servers are alive
for port in 8361 8362 8364 8366 8367 8368 8369 8380 8381; do
  info=$(curl -s "http://localhost:$port/" --max-time 2 2>/dev/null)
  [ -n "$info" ] && echo "Port $port: $info" | head -c 200
  echo ""
done

# 2. Check health of a specific server
curl -s "http://localhost:8368/health"
# → {"status": "healthy", "server": "git-context", "port": 8368}

# 3. Find routes if HTTP 404 on /tools (read the source)
cat /proc/$(pgrep -f "port 8368")/cmdline | tr '\0' ' '  # get script
# then grep for route definitions in the source
```

### Calling Tools

```bash
# Pattern: POST to /tools/<tool_name> with JSON body
curl -s -X POST "http://localhost:8368/tools/git_status" \
  -H "Content-Type: application/json" \
  -d '{"repo_path": "/path/to/repo"}' | python3 -m json.tool

# Memory server - create entity (tool names inferred from root endpoint, verify before use)
curl -s -X POST "http://localhost:8366/tools/memory_create_entity" \
  -H "Content-Type: application/json" \
  -d '{"name": "concept-name", "type": "concept", "observations": ["key fact"]}'

# Memory server - search
curl -s -X POST "http://localhost:8366/tools/memory_search" \
  -H "Content-Type: application/json" \
  -d '{"query": "vault maintenance", "limit": 5}'

# Sequential thinking (tool names inferred from root endpoint, verify before use)
curl -s -X POST "http://localhost:8367/tools/thinking_think" \
  -H "Content-Type: application/json" \
  -d '{"thought": "How should I structure the vault maintenance?", "session_id": "vault-001"}'

# Security scan (tool names inferred from root endpoint, verify before use)
curl -s -X POST "http://localhost:8369/tools/security_scan_file" \
  -H "Content-Type: application/json" \
  -d '{"file_path": "/path/to/file.py"}'

# Git context (always specify repo_path — default is cohezion platform, not vault)
curl -s -X POST "http://localhost:8368/tools/git_status" \
  -H "Content-Type: application/json" \
  -d '{"repo_path": "/home/mike-anderson/vaults/cohezion-vault"}' | python3 -m json.tool
```

## Common Gotchas

### SurrealDB Read-Only Mode

SurrealDB on port 8000 may start in read-only mode:

```
{"status": "ERR", "result": "Couldn't write to a read only transaction"}
```

SELECT queries still work; INSERT/UPDATE/DELETE fail. To enable writes, restart with write mode enabled (check `tools/cohezion-engine` startup scripts).

### Git Context Default Repo

The Git Context server (8368) defaults to `/home/mike-anderson/dev/cohezion` (the platform repo), NOT the vault. Always pass `repo_path` explicitly:

```bash
# Wrong — returns platform repo status
curl -s -X POST "http://localhost:8368/tools/git_status" \
  -H "Content-Type: application/json" -d '{}'

# Correct — returns vault status
curl -s -X POST "http://localhost:8368/tools/git_status" \
  -H "Content-Type: application/json" \
  -d '{"repo_path": "/home/mike-anderson/vaults/cohezion-vault"}'
```

### Non-REST Servers

Ports 8364, 8380, 8381 return HTTP 000 (connection refused or non-HTTP protocol). They may use SSE or WebSocket transport and are not callable via simple curl.

## When to Use Each Server

| Need | Server | Tool |
|------|--------|------|
| Vault git status | 8368 Git Context | `git_status` (with repo_path!) |
| Store cross-session knowledge | 8366 Memory | `memory_create_entity`, `memory_add_observation` |
| Structured reasoning trace | 8367 Sequential | `thinking_think`, `thinking_branch` |
| Security audit | 8369 Security | `security_scan_project`, `security_get_checklist` |
| BMAD workflows | 8361 BMAD | (endpoint pattern TBD — needs source check) |

## Source Discovery Pattern

If a server returns 404 on `/tools/<name>`, find the actual routes:

```bash
# 1. Find the PID and source script
ss -tlnp | grep 836X  # find PID
cat /proc/<PID>/cmdline | tr '\0' ' '  # get script path

# 2. Read the source for route definitions
rg "routes|add_route|app\.router" /path/to/server.py

# 3. Common patterns found in Cohezion servers
# @routes.post("/tools/tool_name")   ← most common
# @app.route("/api/tool_name")        ← alternative
# app.add_routes(routes)              ← aiohttp pattern
```
