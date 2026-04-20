# BMAD MCP Infrastructure - Setup Guide

## Quick Start

### 1. Start Redis (already done)
```bash
docker run -d --name redis-mcp -p 6379:6379 redis:7-alpine redis-server --appendonly yes
```

### 2. Start BMAD MCP Server
```bash
cd /home/mike-anderson/dev/cohezion
python3 -m uvicorn cohezion.mcp.servers.bmad.server:app --host 0.0.0.0 --port 8361 --reload
```

Or with the server manager:
```bash
python3 -m cohezion.mcp.manager.server_manager
```

### 3. Test the Server
```bash
curl http://localhost:8361/health
curl http://localhost:8361/
```

### 4. Use a Tool
```bash
curl -X POST http://localhost:8361/tools/bmad_help \
  -H "Content-Type: application/json" \
  -d '{"query": "create a prd"}'
```

## Available Tools (20 Core)

| Tool | Description |
|------|-------------|
| `bmad_help` | Interactive help system |
| `bmad_bmm_create_prd` | Create Product Requirements Document |
| `bmad_bmm_create_story` | Create user stories |
| `bmad_bmm_sprint_planning` | Plan sprints |
| `bmad_bmm_dev_story` | Develop stories |
| `bmad_bmm_code_review` | Code review |
| `bmad_gds_create_game_brief` | Create game design brief |
| `bmad_gds_game_architecture` | Game architecture |
| `bmad_cis_brainstorming` | Brainstorming session |
| `bmad_tea_test_design` | Test design |
| `bmad_bmb_create_agent` | Create custom agents |
| `bmad_party_mode` | Multi-agent collaboration |
| `bmad_list_workflows` | List workflows |
| `bmad_list_agents` | List agents |
| `bmad_index_docs` | Index documentation |
| `bmad_status` | Server status |

## Architecture

```
┌─────────────────────────────────────────────┐
│           Your VM (125GB RAM)              │
│                                             │
│  ┌───────────────────────────────────────┐  │
│  │  Redis Server (Port 6379)            │  │
│  │  • Session persistence               │  │
│  │  • State management                  │  │
│  └───────────────────────────────────────┘  │
│                   │                         │
│  ┌────────────────┴──────────────────────┐ │
│  │          BMAD MCP Server (8361)      │ │
│  │  • 20 core tools (108 planned)       │ │
│  │  • 28 agents                         │ │
│  │  • 6 modules                         │ │
│  └────────────────────────────────────────┘ │
└─────────────────────────────────────────────┘
```

## Configuration

### Environment Variables
- `MCP_PORT`: Server port (default: 8361)
- `REDIS_URL`: Redis connection (default: redis://localhost:6379)
- `BMAD_DATA_PATH`: Path to _bmad directory (default: ./_bmad)
- `LOG_LEVEL`: Logging level (default: INFO)

### Files Created
```
src/cohezion/mcp/
├── servers/
│   └── bmad/
│       ├── __init__.py
│       ├── server.py          # Main server
│       └── engine.py          # BMAD engine
├── shared/
│   ├── __init__.py
│   ├── session.py            # Redis session manager
│   └── logging.py            # Vault logging
└── manager/
    └── server_manager.py     # MCP orchestrator

.opencode/commands/          # Native opencode commands
.zed/                       # Zed IDE integration
.antigravity/               # Antigravity IDE integration
.vscode/                    # VS Code integration
.mcp/                       # MCP configurations
cloud-vault-mcp/vault/      # Documentation
```

## Next Steps

1. **Platform Integrations**: Create native commands for opencode, Zed, Antigravity
2. **Skills.sh MCP**: Build server for 85K+ skills
3. **Complete BMAD**: Add remaining 88 tools
4. **Cloud Access**: Setup ngrok tunnel
5. **Documentation**: Complete vault docs

## Troubleshooting

### Redis Connection Issues
```bash
docker ps | grep redis-mcp  # Check if running
docker logs redis-mcp       # View logs
```

### Port Already in Use
```bash
lsof -i :8361  # Check what's using port 8361
kill -9 <PID>  # Kill process if needed
```

### Import Errors
```bash
pip install redis aiohttp  # Install dependencies
```
