# Cloud Vault MCP Server

A Model Context Protocol (MCP) server providing AI agents with read/write access to a structured Obsidian knowledge vault for compound engineering.

## What is This?

This server enables AI agents (like Claude Code) to:

- **Read and write** markdown notes in an Obsidian vault
- **Search** across all vault content with full-text search
- **Log decisions** (Architecture Decision Records)
- **Log experiments** (hypothesis, method, results, learnings)
- **Extract patterns** (reusable solutions from project work)
- **Find relevant context** from prior work before starting new tasks

The vault becomes a **persistent memory layer** that accumulates reusable knowledge across AI-assisted work sessions.

## Quick Start

```bash
# 1. Run setup
./setup.sh

# 2. Save the API key displayed

# 3. Configure Claude Code in ~/.claude/mcp.json:
{
  "mcpServers": {
    "cloud-vault": {
      "type": "streamable-http",
      "url": "http://localhost:8360/mcp",
      "headers": {
        "Authorization": "Bearer <YOUR_API_KEY>"
      }
    }
  }
}

# 4. Verify
curl http://localhost:8360/health
```

See [QUICKSTART.md](./QUICKSTART.md) for detailed examples.

## Features

### Core Vault Operations
- Read, write, edit, delete notes
- List directory contents
- Full-text search with folder scoping

### Obsidian Integration
- Backlink and forward link discovery
- Tag extraction and search
- Template-based note creation
- Wikilink support

### Compound Engineering
- **Log decisions**: Create Architecture Decision Records (ADRs)
- **Log experiments**: Track hypotheses, methods, results, learnings
- **Extract patterns**: Save reusable solutions for future use
- **Find context**: Search prior decisions, patterns, and experiments

### Git Integration
- Vault is a Git repository (all changes tracked)
- Auto-sync service (commits every 5 minutes)
- Optional push to remote for backup

## Architecture

```
Client (Claude Code, Python)
    │
    │ HTTP + Bearer Token Auth
    ▼
MCP Server (FastMCP)
    │
    ├─ VaultOps (core filesystem operations)
    ├─ ObsidianOps (backlinks, tags, templates)
    └─ CompoundOps (decisions, experiments, patterns)
        │
        ▼
    Obsidian Vault (Git repo)
        ├── projects/
        ├── decisions/
        ├── patterns/
        ├── experiments/
        ├── papers/
        ├── daily/
        ├── concepts/
        ├── tools/
        └── inbox/
```

## Project Structure

```
cloud-vault-mcp/
├── src/mcp_server/
│   ├── main.py           # Server entry point
│   ├── server.py         # MCP tool definitions
│   ├── vault_ops.py      # Core vault filesystem operations
│   ├── obsidian_ops.py   # Obsidian-specific features
│   ├── compound_ops.py   # Compound engineering workflows
│   ├── auth.py           # API key authentication
│   └── config.py         # Configuration management
├── vault/                # Obsidian vault (Git repo)
│   ├── decisions/        # Architecture Decision Records
│   ├── patterns/         # Reusable solutions
│   ├── experiments/      # Hypothesis and results
│   ├── projects/         # Per-project documentation
│   ├── papers/           # Literature notes
│   ├── daily/            # Daily logs
│   ├── concepts/         # Evergreen notes
│   ├── tools/            # Tool configurations
│   └── inbox/            # Quick capture
├── deploy/
│   └── nginx/            # Nginx config for TLS
├── tests/                # Pytest test suite
├── docker-compose.yml    # Container orchestration
├── Dockerfile            # Server container image
├── setup.sh              # One-command setup script
├── .env.example          # Configuration template
├── pyproject.toml        # Python package definition
├── QUICKSTART.md         # 5-minute setup guide
└── README.md             # This file
```

## Documentation

- **[QUICKSTART.md](./QUICKSTART.md)** - 5-minute setup and basic examples
- **[/docs/mcp-integration.md](/home/mike-anderson/dev/cohezion/docs/mcp-integration.md)** - Complete integration guide
  - Setup and configuration
  - Client integration (Claude Code, Python)
  - Usage examples
  - Troubleshooting
  - Security considerations

## Available MCP Tools

### Core Operations
- `vault_read(path)` - Read note content
- `vault_write(path, content)` - Create/overwrite note
- `vault_edit(path, edits)` - Apply surgical edits
- `vault_delete(path)` - Delete note
- `vault_list(directory, recursive)` - List contents
- `vault_search(query, scope, folder)` - Full-text search

### Obsidian Features
- `vault_backlinks(path)` - Find notes linking TO this note
- `vault_forward_links(path)` - Find notes this note links TO
- `vault_tags(path)` - List tags (vault-wide or per-note)
- `vault_create_from_template(template, target, vars)` - Create from template

### Compound Engineering
- `vault_log_decision(project, title, context, decision, rationale, alternatives)` - Create ADR
- `vault_log_experiment(project, hypothesis, method, result, learnings)` - Log experiment
- `vault_extract_pattern(source, name, description, code, domain)` - Save pattern
- `vault_find_relevant_context(query, project)` - Search all knowledge

## Configuration

Edit `.env`:

```bash
MCP_API_KEY=<sha256-hash>           # Required: API key for auth
MCP_PORT=8360                       # Server port
VAULT_PATH=/vault                   # Vault directory
CORS_ORIGINS=*                      # CORS allowed origins
LOG_LEVEL=info                      # Logging level
GIT_SYNC_INTERVAL=300               # Auto-commit interval (seconds)
GIT_REMOTE_URL=                     # Optional: remote backup URL
```

## Deployment

### Docker (Recommended)

```bash
# Start MCP server
docker compose up -d mcp-server

# Optional: Start git auto-sync
docker compose up -d git-sync

# Optional: Start nginx (requires TLS certs)
docker compose up -d nginx
```

### Local Development

```bash
./setup.sh --dev
export VAULT_PATH=$(pwd)/vault
source .env
python -m mcp_server.main
```

## Usage Examples

### Python Client

```python
import requests

def call_tool(tool, **args):
    return requests.post(
        'http://localhost:8360/mcp/tools/call',
        headers={'Authorization': f'Bearer {API_KEY}'},
        json={'tool': tool, 'arguments': args}
    ).json()

# Log a decision
call_tool(
    'vault_log_decision',
    project='my-project',
    title='Use FastMCP',
    context='Need MCP server framework',
    decision='Use FastMCP library',
    rationale='High-level API, less boilerplate'
)

# Search for context
results = call_tool(
    'vault_find_relevant_context',
    query='token efficiency',
    project='cohezion'
)
```

### Claude Code

Once configured in `~/.claude/mcp.json`, Claude Code automatically sees all MCP tools and can:

- Read project documentation from vault
- Log decisions when making architectural choices
- Search for similar past problems before implementing
- Extract patterns when discovering reusable solutions
- Log experiments when testing new approaches

## Security

- **API key authentication**: SHA-256 hash-based keys
- **HTTPS support**: Via nginx (configure TLS certs in `deploy/nginx/certs/`)
- **CORS configuration**: Restrict origins via `CORS_ORIGINS`
- **Vault isolation**: Each server instance has its own vault
- **Git history**: All changes are versioned and auditable

Never commit API keys to Git. Use environment variables.

## Testing

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/

# With coverage
pytest --cov=mcp_server tests/
```

## Requirements

- Python 3.11+
- Docker and Docker Compose (for containerized deployment)
- Git (vault versioning)

## Dependencies

- `mcp[cli]>=1.2.0` - Model Context Protocol SDK
- `pyyaml>=6.0` - YAML parsing
- `uvicorn>=0.30.0` - ASGI server
- `starlette>=0.38.0` - Web framework

## License

Part of the cohezion project. See main repository for license details.

## Contributing

This MCP server is part of the cohezion agentic AI framework. For integration questions or feature requests, see the main cohezion documentation.

## Roadmap

- [ ] Full-text search indexing (Whoosh/Elasticsearch)
- [ ] Webhook notifications for vault changes
- [ ] Multi-user support with per-user auth
- [ ] Obsidian plugin for bi-directional sync
- [ ] Graph query API for knowledge graph exploration
- [ ] Automated pattern extraction from commit history

## Links

- Main cohezion repository: `/home/mike-anderson/dev/cohezion/`
- Full documentation: [/docs/mcp-integration.md](/home/mike-anderson/dev/cohezion/docs/mcp-integration.md)
- MCP Protocol: https://modelcontextprotocol.io/
- FastMCP: https://github.com/jlowin/fastmcp
- Obsidian: https://obsidian.md/
