---
name: mcp-infrastructure-architecture
description: Architecture Decision Records and technical design for Universal MCP Server Infrastructure
version: 1.0.0
status: accepted
owner: mike-anderson
date: 2026-03-05
---

# Architecture: Universal MCP Server Infrastructure

## 1. Overview

### Context
We need to make BMAD (108 commands) available across all IDEs and cloud platforms while maintaining flexibility to add unlimited future MCP servers.

### Goals
1. **Universal Access**: BMAD works in 5+ IDEs + cloud
2. **State Persistence**: Sessions survive platform switches
3. **Extensibility**: Add new MCP servers in <30 min
4. **Self-Hosted**: Local VM with optional cloud tunnel
5. **Skill Integration**: Access Skills.sh ecosystem

### Constraints
- Local VM (125GB RAM, 1.2TB disk)
- Must support 20-50 MCP servers
- Redis for state management
- HTTP/SSE transport for cloud compatibility

---

## 2. High-Level Architecture

### System Context Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              USERS                                         │
│  Developers  │  Team Leads  │  Cloud Users  │  Architects                   │
└─────────────┴──────────────┴───────────────┴───────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         PLATFORM LAYER                                      │
│  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────────┐ │
│  │ opencode  │ │   Zed     │ │Antigravity│ │ VS Code   │ │ Claude Code   │ │
│  │           │ │           │ │           │ │           │ │  (native+MCP) │ │
│  │ 111 cmds  │ │ MCP only  │ │ MCP only  │ │ MCP only  │ │               │ │
│  └───────────┘ └───────────┘ └───────────┘ └───────────┘ └───────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      │ HTTP/REST
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         MCP LAYER                                           │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                    MCP SERVER MANAGER (8370)                           │ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────────┐   │ │
│  │  │ Port        │  │ Health      │  │  Auto-restart               │   │ │
│  │  │ Allocator   │  │ Monitor     │  │  (max 5)                    │   │ │
│  │  └─────────────┘  └─────────────┘  └─────────────────────────────┘   │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                      │                                      │
│  ┌───────────────┐  ┌───────────────┐  ┌─────────────────────────────────┐ │
│  │  BMAD MCP     │  │  Skills.sh    │  │  Future Servers (8363-8399)     │ │
│  │  Port: 8361   │  │  Port: 8362   │  │                                 │ │
│  │               │  │               │  │                                 │ │
│  │ • 108 tools   │  │ • 85K+ skills │  │ • Custom APIs                   │ │
│  │ • 28 agents   │  │ • Search      │  │ • Databases                     │ │
│  │ • Workflows   │  │ • Install     │  │ • Any service                   │ │
│  │ • Resources   │  │ • Execute     │  │                                 │ │
│  └───────────────┘  └───────────────┘  └─────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      │ Pub/Sub
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         STATE LAYER                                         │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                    REDIS SERVER (6379)                                   │ │
│  │  ┌─────────────────────┐ ┌─────────────────────┐ ┌──────────────────┐ │ │
│  │  │ bmad:session:*      │ │ skills:cache:*      │ │ mcp:server:*       │ │ │
│  │  │ Session state     │ │ Skill content       │ │ Server registry  │ │ │
│  │  │ TTL: 1 hour       │ │ TTL: 24 hours       │ │                   │ │ │
│  │  └─────────────────────┘ └─────────────────────┘ └──────────────────┘ │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      │ HTTPS
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         CLOUD LAYER (Optional)                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                    NGROK TUNNEL                                        │ │
│  │  https://bmad-mcp-yourname.ngrok.io ──▶ http://localhost:8361        │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Component Architecture

### 3.1 MCP Server Manager (Port 8370)

**Responsibilities**:
- Port allocation (8360-8399)
- Health monitoring (30s intervals)
- Auto-restart on failure
- Unified logging

**Key Classes**:
```python
class MCPServerManager:
    - port_allocator: PortAllocator
    - servers: Dict[str, MCPServerConfig]
    - health_check_task: asyncio.Task
    
    + register_server(name, entry_point, port)
    + start_server(name)
    + stop_server(name)
    + health_check(name)
    + health_check_loop()

class PortAllocator:
    - port_range: range(8360, 8400)
    - allocated: Dict[int, str]
    
    + allocate(server_name, preferred_port)
    + release(server_name)
```

**API Endpoints**:
```
GET    /                   - Status
GET    /health             - Health check
POST   /servers/{name}/start
POST   /servers/{name}/stop
POST   /servers/{name}/restart
GET    /servers/{name}/health
```

### 3.2 BMAD MCP Server (Port 8361)

**Responsibilities**:
- Execute 108 BMAD tools
- Load workflows/agents from disk
- Manage BMAD-specific sessions

**Key Classes**:
```python
class BMADEngine:
    - data_path: Path
    - modules: Dict[str, Module]
    - workflows: Dict[str, Workflow]
    - agents: Dict[str, Agent]
    
    + load_workflow(module, path)
    + load_agent(agent_id)
    + execute_workflow(workflow, params, session)
    + analyze_context(context)
    + get_next_steps(query, analysis)

class BMADMCPHandler:
    - engine: BMADEngine
    - session_manager: SessionManager
    
    + tool_bmad_help()
    + tool_bmad_bmm_create_prd()
    + tool_bmad_list_workflows()
    + resource_workflows()
    + resource_agents()
```

**API Design**:
```
POST   /tools/{tool_name}          - Execute tool
GET    /resources/workflows/{path}  - Get workflow
GET    /resources/agents/{id}      - Get agent
GET    /resources/modules          - List modules
GET    /health                     - Health check
GET    /                           - Server info
```

### 3.3 Skills.sh MCP Server (Port 8362)

**Responsibilities**:
- Search skills.sh registry
- Install skills locally
- Execute skills (fetch content)
- Manage local cache

**Key Classes**:
```python
class SkillsShClient:
    - base_url: "https://skills.sh"
    
    + search_skills(query, category, limit)
    + get_skill(owner, repo)
    + get_skill_content(owner, repo)
    + list_categories()
    + get_trending(limit)

class SkillsCache:
    - max_size: 1000
    - ttl: 86400 seconds
    
    + get(skill_id)
    + set(skill_id, data)
    + get_content(skill_id)
    + set_content(skill_id, content)
    + invalidate(skill_id)

class SkillsMCPHandler:
    - client: SkillsShClient
    - cache: SkillsCache
    
    + tool_skills_search()
    + tool_skills_get()
    + tool_skills_install()
    + tool_skills_execute()
    + tool_skills_cache_info()
```

### 3.4 Shared Components

#### Session Manager
```python
class SessionManager:
    - redis_url: str
    - prefix: str
    
    + create_session(session_id, data)
    + get_session(session_id)
    + update_session(session_id, data)
    + delete_session(session_id)
```

#### Vault Logger
```python
class VaultLogger:
    - server_name: str
    - log_file: Path
    
    + debug(msg)
    + info(msg)
    + warning(msg)
    + error(msg)
```

---

## 4. Data Architecture

### 4.1 Redis Schema

```
# Session keys (1 hour TTL)
bmad:session:{session_id}           → Session data
skills:cache:{skill_id}             → Skill metadata
skills:cache:content:{skill_id}     → Skill content
mcp:server:{name}                   → Server registration
mcp:metrics:{name}                  → Server metrics

# Key prefixes
- bmad:        BMAD-specific data
- skills:      Skills.sh cache
- mcp:         MCP infrastructure
- session:     Session data (auto-prefixed)
```

### 4.2 File System Schema

```
_bmad/
├── bmm/                    # Business Method Module
│   ├── workflows/          # Workflow definitions
│   └── agents/             # Agent personas
├── gds/                    # Game Dev Studio
├── cis/                    # Creative Intelligence
├── tea/                    # Test Architecture
├── bmb/                    # BMAD Builder
└── core/                   # Core utilities

src/cohezion/mcp/
├── manager/                # Server manager
├── servers/
│   ├── bmad/               # BMAD MCP server
│   └── skills/             # Skills.sh MCP server
└── shared/                 # Shared utilities
```

---

## 5. API Design

### 5.1 Transport Protocol

**Decision**: HTTP/REST instead of stdio
- **Rationale**: Cloud compatibility (Claude.ai/code)
- **Trade-off**: Slightly more overhead, but universal access
- **Alternative**: stdio for local-only (rejected)

### 5.2 Response Format

```json
{
  "tool": "tool_name",
  "status": "success|error",
  "data": { ... },
  "message": "Human-readable message",
  "session_id": "uuid"
}
```

### 5.3 Error Handling

```json
{
  "error": "Error description",
  "code": "ERROR_CODE",
  "details": { ... }
}
```

HTTP Status Codes:
- 200: Success
- 400: Bad request
- 404: Not found
- 500: Server error

---

## 6. Deployment Architecture

### 6.1 Docker Compose

```yaml
services:
  redis-mcp:        # Port 6379
  bmad-mcp:         # Port 8361
  skills-mcp:       # Port 8362
  mcp-manager:      # Port 8370
  ngrok:            # Cloud tunnel (optional)
```

### 6.2 Local Development

```bash
# Direct Python execution
python3 -m cohezion.mcp.servers.bmad.server
python3 -m cohezion.mcp.servers.skills.server
python3 -m cohezion.mcp.manager.server_manager
```

### 6.3 Production Considerations

**Security**:
- API key authentication for cloud access
- TLS via ngrok (free tier) or Cloudflare
- Local network only by default

**Monitoring**:
- Health checks every 30s
- Vault logging for all operations
- Prometheus metrics (future)

**Scaling**:
- Horizontal: Run on multiple VMs
- Load balancer in front
- Shared Redis cluster

---

## 7. Key Architectural Decisions

### ADR-1: HTTP/SSE over stdio

**Status**: ✅ Accepted

**Context**: Need to support Claude.ai/code which requires HTTP transport.

**Decision**: Use HTTP/REST for all MCP servers.

**Consequences**:
- ✅ Cloud compatible
- ✅ Easy to debug (curl)
- ✅ Standard tooling
- ❌ Slightly more resource usage
- ❌ Need to manage ports

### ADR-2: Redis for State Management

**Status**: ✅ Accepted

**Context**: Need session persistence across platforms and servers.

**Decision**: Use Redis with key prefixing for isolation.

**Consequences**:
- ✅ Fast session access
- ✅ Persistence across restarts
- ✅ Pub/sub for coordination
- ❌ Additional dependency
- ❌ Memory overhead (~100MB)

### ADR-3: Port Range 8360-8399

**Status**: ✅ Accepted

**Context**: Need centralized port management to avoid conflicts.

**Decision**: Reserve 8360-8399 for MCP servers, managed by MCP Manager.

**Consequences**:
- ✅ Predictable port allocation
- ✅ Easy firewall rules
- ✅ No conflicts with other services
- ❌ Limited to 40 servers (sufficient for current needs)

### ADR-4: File-Based Workflow Loading

**Status**: ✅ Accepted

**Context**: BMAD has 696 markdown files in `_bmad/`.

**Decision**: Load directly from disk with file watcher for hot reload.

**Consequences**:
- ✅ No rebuild needed for workflow changes
- ✅ Version controlled workflows
- ✅ Simple editing
- ❌ Disk I/O on every load (mitigated by caching)

### ADR-5: Skills.sh Cache with 24h TTL

**Status**: ✅ Accepted

**Context**: Skills.sh has 85K+ skills, don't want to fetch every time.

**Decision**: Cache top 1000 skills in Redis with 24-hour TTL.

**Consequences**:
- ✅ Fast skill access
- ✅ Reduced API calls
- ✅ Works offline for cached skills
- ❌ Stale data possible
- ❌ Cache invalidation complexity

### ADR-6: Dual Mode for opencode/Claude Code

**Status**: ✅ Accepted

**Context**: Some platforms benefit from native commands.

**Decision**: Provide both native commands AND MCP client for opencode/Claude.

**Consequences**:
- ✅ Best of both worlds
- ✅ Fast native commands
- ✅ Advanced features via MCP
- ❌ More maintenance
- ❌ Potential confusion

---

## 8. Technology Stack

| Layer | Technology | Version | Purpose |
|-------|------------|---------|---------|
| Language | Python | 3.11+ | Server implementation |
| Web Framework | aiohttp | 3.8+ | HTTP server |
| Cache/State | Redis | 7.x | Session storage |
| Container | Docker | 20.10+ | Deployment |
| Tunnel | ngrok | latest | Cloud access |
| Protocol | MCP | 2024 | AI integration |

---

## 9. Security Architecture

### 9.1 Threat Model

**Assets**:
- MCP API endpoints
- Redis data
- Session information
- Workflow/agent content

**Threats**:
1. Unauthorized API access
2. Session hijacking
3. Redis injection
4. Port scanning

### 9.2 Mitigations

| Threat | Mitigation |
|--------|------------|
| Unauthorized access | API key validation (optional) |
| Session hijacking | Secure session IDs, HTTPS |
| Redis injection | Input validation, parameterized queries |
| Port scanning | Bind to localhost by default |
| DDoS | Rate limiting (future) |

### 9.3 Security Checklist

- [x] Local-only by default
- [x] API key framework ready
- [x] HTTPS for cloud (ngrok)
- [ ] Rate limiting (P2)
- [ ] Audit logging (P2)
- [ ] Input validation (P1)

---

## 10. Performance Architecture

### 10.1 Target Metrics

| Metric | Target | Current |
|--------|--------|---------|
| Response time | <100ms | ~50ms |
| Memory usage | <300MB | ~270MB |
| Concurrent users | 1000+ | Redis supports 10K+ |
| Cold start | <5s | ~3s |

### 10.2 Optimization Strategies

1. **Redis Pipeline**: Batch operations
2. **Async I/O**: Non-blocking everywhere
3. **Skill Cache**: 1000 skills cached locally
4. **Workflow Caching**: In-memory after first load
5. **Connection Pooling**: Reuse Redis connections

### 10.3 Bottlenecks

| Bottleneck | Impact | Mitigation |
|------------|--------|------------|
| Skills.sh API latency | High | Cache hit rate 90%+ |
| Disk I/O (workflows) | Medium | In-memory caching |
| Redis memory | Low | 1 hour TTL on sessions |

---

## 11. Testing Strategy

### 11.1 Test Pyramid

```
    /\
   /  \  E2E Tests (5%)
  /----\  Integration (15%)
 /------\  Unit Tests (80%)
/________\
```

### 11.2 Test Coverage

| Component | Coverage Target | Current |
|-------------|-----------------|---------|
| BMAD Engine | 80% | ⏳ |
| Skills Client | 80% | ⏳ |
| Session Manager | 90% | ⏳ |
| API Endpoints | 70% | ⏳ |

### 11.3 Testing Tools

- **Unit**: pytest with asyncio support
- **Integration**: TestClient from aiohttp
- **E2E**: curl scripts + validation
- **Load**: Locust (future)

---

## 12. Monitoring & Observability

### 12.1 Logging

**Vault Logger**: All servers log to `cloud-vault-mcp/vault/logs/`

Format:
```json
{
  "timestamp": "2026-03-05T21:00:00Z",
  "server": "bmad",
  "level": "INFO",
  "message": "Server started",
  "source": "server.py:42"
}
```

### 12.2 Health Checks

```
GET /health → {
  "status": "healthy|unhealthy",
  "port": 8361,
  "uptime": 3600,
  "redis_connected": true
}
```

### 12.3 Metrics (Future)

- Request count
- Response time histogram
- Error rate
- Cache hit rate
- Session count

---

## 13. Migration Path

### From Existing BMAD (Claude Code only)

```
Phase 1: Deploy MCP servers locally
  - Install Redis
  - Start BMAD MCP (8361)
  - Test with curl

Phase 2: Add platform support
  - Copy commands to .opencode/
  - Create MCP configs
  - Test each platform

Phase 3: Enable cloud access
  - Configure ngrok
  - Update .mcp.json.cloud
  - Test from Claude.ai/code

Phase 4: Decommission legacy
  - Keep .claude/commands/ for backward compat
  - Route through MCP for new features
```

---

## 14. Future Enhancements

### 14.1 Near Term (1-2 weeks)

- [ ] Complete remaining 88 BMAD tools
- [ ] Add authentication layer
- [ ] Implement rate limiting
- [ ] Add more skills categories

### 14.2 Medium Term (1-2 months)

- [ ] Web UI for monitoring
- [ ] Prometheus metrics
- [ ] Alerting integration
- [ ] Backup/restore for Redis

### 14.3 Long Term (3-6 months)

- [ ] Multi-VM support
- [ ] Load balancing
- [ ] Custom skill creation UI
- [ ] Integration marketplace

---

## 15. Appendix

### A. Glossary

- **MCP**: Model Context Protocol - standard for AI tool integration
- **BMAD**: Business Method for AI Development - 108 command methodology
- **Skills.sh**: Registry of 85K+ AI skills
- **Redis**: In-memory data store for sessions

### B. References

- MCP Specification: https://modelcontextprotocol.io
- Skills.sh: https://skills.sh
- BMAD Repository: https://github.com/bmad-code-org/BMAD-METHOD

### C. Document History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0.0 | 2026-03-05 | Initial architecture | mike-anderson |

---

**Status**: Accepted
**Next Review**: 2026-03-12
