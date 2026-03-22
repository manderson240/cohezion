# Cloud Vault MCP Server Integration

## Overview

The Cloud Vault MCP Server provides a Model Context Protocol (MCP) interface for cohezion's compound engineering system. It enables AI agents to read, write, search, and organize knowledge in a structured Obsidian vault, creating a persistent memory layer that accumulates reusable context across sessions.

## Architecture

```
┌─────────────────┐         ┌──────────────────┐         ┌─────────────────┐
│  Cohezion Core  │ ◄─────► │  MCP Server      │ ◄─────► │ Obsidian Vault  │
│  (Client)       │  HTTP   │  (cloud-vault)   │  FS     │  (Git Repo)     │
└─────────────────┘         └──────────────────┘         └─────────────────┘
                                     │
                                     ▼
                            ┌─────────────────┐
                            │   Git Sync      │
                            │   (Optional)    │
                            └─────────────────┘
```

The server provides three categories of operations:

1. **Core Vault Operations**: Read, write, edit, delete, list, search
2. **Obsidian-Aware Operations**: Backlinks, forward links, tags, templates
3. **Compound Engineering Operations**: Log decisions, experiments, patterns; find context

## Setup

### Prerequisites

- Python 3.11+
- Docker and Docker Compose (for containerized deployment)
- Git (vault is versioned)

### Quick Start (Docker)

1. **Clone and navigate to the MCP server directory**:
   ```bash
   cd /home/mike-anderson/dev/cohezion/cloud-vault-mcp
   ```

2. **Run the setup script**:
   ```bash
   ./setup.sh
   ```

   This script will:
   - Create `.env` from `.env.example`
   - Generate a secure API key (SHA-256 hash)
   - Initialize the vault as a Git repository
   - Build and start the Docker container

3. **Save the API key** displayed during setup. You'll need it for client configuration.

4. **Verify the server is running**:
   ```bash
   curl http://localhost:8360/health
   ```

   Expected response: `{"status":"ok"}`

### Development Setup (Local Python)

For local development without Docker:

```bash
cd /home/mike-anderson/dev/cohezion/cloud-vault-mcp
./setup.sh --dev
```

Then start the server:

```bash
export VAULT_PATH=$(pwd)/vault
source .env
export MCP_API_KEY MCP_PORT
cloud-vault-mcp
```

Or run directly:

```bash
VAULT_PATH=$(pwd)/vault \
MCP_API_KEY=$(grep MCP_API_KEY .env | cut -d= -f2) \
python -m mcp_server.main
```

### Configuration

Edit `.env` to customize server settings:

```bash
# API key for authentication (required)
MCP_API_KEY=<your-generated-key>

# Server port (default: 8360)
MCP_PORT=8360

# Vault path (default: /vault in Docker, ./vault locally)
VAULT_PATH=/vault

# CORS allowed origins (default: *)
CORS_ORIGINS=*

# Log level (default: info)
LOG_LEVEL=info

# Git sync interval in seconds (default: 300 = 5 minutes)
GIT_SYNC_INTERVAL=300

# Optional: Git remote URL for vault backup
GIT_REMOTE_URL=
```

## Client Configuration

### Claude Code Integration

Add the MCP server to your Claude Code configuration:

**Option 1: Global config** (`~/.claude/mcp.json`):
```json
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
```

**Option 2: Project-specific config** (`.mcp.json` in project root):
```json
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
```

Replace `<YOUR_API_KEY>` with the key generated during setup.

### Cohezion Integration

The cohezion core can connect to the MCP server through the `ContextEngineeringInfrastructure` class:

```python
from cohezion.core.context_engineering import ContextEngineeringInfrastructure
import requests

class VaultMCPClient:
    """Client for Cloud Vault MCP Server."""

    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip('/')
        self.headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }

    def call_tool(self, tool_name: str, **kwargs):
        """Call an MCP tool by name."""
        response = requests.post(
            f'{self.base_url}/mcp/tools/call',
            headers=self.headers,
            json={'tool': tool_name, 'arguments': kwargs}
        )
        response.raise_for_status()
        return response.json()

    def vault_read(self, path: str) -> str:
        """Read a note from the vault."""
        return self.call_tool('vault_read', path=path)

    def vault_write(self, path: str, content: str) -> str:
        """Write a note to the vault."""
        return self.call_tool('vault_write', path=path, content=content)

    def vault_search(self, query: str, scope: str = 'all', folder: str = '') -> dict:
        """Search the vault."""
        return self.call_tool('vault_search', query=query, scope=scope, folder=folder)

    def log_decision(self, project: str, title: str, context: str,
                    decision: str, rationale: str,
                    alternatives_considered: str = '') -> str:
        """Log an architecture decision."""
        return self.call_tool(
            'vault_log_decision',
            project=project,
            title=title,
            context=context,
            decision=decision,
            rationale=rationale,
            alternatives_considered=alternatives_considered
        )

    def find_relevant_context(self, query: str, project: str = '') -> dict:
        """Find relevant prior decisions, patterns, and experiments."""
        return self.call_tool(
            'vault_find_relevant_context',
            query=query,
            project=project
        )

# Wire into ContextEngineeringInfrastructure
infra = ContextEngineeringInfrastructure()
vault_client = VaultMCPClient(
    base_url='http://localhost:8360',
    api_key='<YOUR_API_KEY>'
)

infra.register_tool('vault_read', vault_client.vault_read)
infra.register_tool('vault_write', vault_client.vault_write)
infra.register_tool('vault_search', vault_client.vault_search)
infra.register_tool('log_decision', vault_client.log_decision)
infra.register_tool('find_context', vault_client.find_relevant_context)
```

## Usage Examples

### Example 1: Log an Architecture Decision

```python
vault_client = VaultMCPClient('http://localhost:8360', api_key)

result = vault_client.log_decision(
    project='cohezion',
    title='Use FastMCP for MCP Server Framework',
    context='Need to build an MCP server for Cloud Vault. FastMCP provides a high-level API over the MCP SDK.',
    decision='Use FastMCP library to implement the MCP server',
    rationale='FastMCP reduces boilerplate, provides decorator-based tool registration, and handles streaming HTTP automatically.',
    alternatives_considered='Raw MCP SDK (more complex), custom HTTP wrapper (reinventing the wheel)'
)

print(result)
# Output: "Created decision: decisions/cohezion/2026-02-07-use-fastmcp-for-mcp-server-framework.md"
```

### Example 2: Search for Prior Context

Before implementing a new feature, search for relevant past decisions and patterns:

```python
# Find decisions about MCP integration
results = vault_client.find_relevant_context(
    query='MCP integration authentication',
    project='cohezion'
)

print(results)
# Returns JSON with matching decisions, patterns, experiments, and concepts
```

### Example 3: Log an Experiment

```python
result = vault_client.call_tool(
    'vault_log_experiment',
    project='cohezion',
    hypothesis='SHA-256 hash-based caching will reduce duplicate LLM calls',
    method='Implemented TokenEfficientClient with SHA-256 content hashing. Ran compound cycle 10 times.',
    result='98% cache hit rate after first run. Token cost reduced from 2.5M to 50K per cycle.',
    learnings='Hash-based caching is highly effective for deterministic prompts. Need to handle non-deterministic cases separately.'
)

print(result)
# Output: "Created experiment: experiments/cohezion/2026-02-07-sha256-caching-token-efficiency.md"
```

### Example 4: Extract a Reusable Pattern

After solving a problem, extract the solution as a pattern:

```python
result = vault_client.call_tool(
    'vault_extract_pattern',
    source_path='projects/cohezion/phase-6-journey-tracking.md',
    pattern_name='Non-Critical Observability Pattern',
    description='Wrap observability features (metrics, journeys, inflection detection) in try/except blocks so they never break execution.',
    code_example='''
try:
    journey_tracker.record(step_data)
except Exception as e:
    logger.debug(f"Non-critical journey tracking failed: {e}")
''',
    domain='observability'
)

print(result)
# Output: "Created pattern: patterns/observability/non-critical-observability-pattern.md"
```

### Example 5: Read and Search Vault

```python
# Read a specific note
content = vault_client.vault_read('decisions/cohezion/2026-02-07-use-fastmcp.md')
print(content)

# Search for notes about "token efficiency"
results = vault_client.vault_search(
    query='token efficiency',
    scope='folder',
    folder='experiments'
)

# List vault contents
import json
response = vault_client.call_tool('vault_list', directory='decisions', recursive=True)
print(response)
```

### Example 6: Work with Templates

Create structured notes using templates:

```python
result = vault_client.call_tool(
    'vault_create_from_template',
    template_name='patterns',
    target_path='patterns/ml/curriculum-learning-reward-shaping.md',
    variables={
        'title': 'Curriculum Learning with Reward Shaping',
        'domain': 'ml',
        'description': 'Gradually increase task difficulty while shaping rewards to guide learning.'
    }
)

print(result)
# Output: "Created note from template: patterns/ml/curriculum-learning-reward-shaping.md"
```

## Available MCP Tools

### Core Vault Operations

- `vault_read(path: str)` - Read a note's content
- `vault_write(path: str, content: str)` - Create or overwrite a note
- `vault_edit(path: str, edits: list[dict])` - Apply surgical edits
- `vault_delete(path: str)` - Delete a note
- `vault_list(directory: str = "", recursive: bool = False)` - List contents
- `vault_search(query: str, scope: str = "all", folder: str = "")` - Full-text search

### Obsidian-Aware Operations

- `vault_backlinks(path: str)` - Find notes linking TO this note
- `vault_forward_links(path: str)` - Find notes this note links TO
- `vault_tags(path: str = "")` - List tags (vault-wide or for a note)
- `vault_create_from_template(template_name: str, target_path: str, variables: dict)` - Create from template

### Compound Engineering Operations

- `vault_log_decision(...)` - Create an Architecture Decision Record (ADR)
- `vault_log_experiment(...)` - Log hypothesis, method, results, learnings
- `vault_extract_pattern(...)` - Extract a reusable pattern
- `vault_find_relevant_context(query: str, project: str = "")` - Search decisions, patterns, experiments

## Vault Structure

The vault organizes notes into semantic directories:

```
vault/
├── projects/        # Per-project documentation and index notes
├── decisions/       # Architecture Decision Records (ADRs)
├── patterns/        # Reusable solutions extracted from projects
├── experiments/     # Hypothesis, method, results, learnings
├── papers/          # Literature notes from arXiv and other sources
├── daily/           # Daily development logs
├── concepts/        # Evergreen notes on technical concepts
├── tools/           # Notes on tools, configurations, environments
└── inbox/           # Quick capture, unsorted notes
```

Each directory contains a `_template.md` for structured note creation.

## Troubleshooting

### Server Won't Start

**Problem**: `docker compose up` fails or server doesn't respond.

**Solutions**:
1. Check if port 8360 is already in use:
   ```bash
   lsof -i :8360
   ```
   Change `MCP_PORT` in `.env` if needed.

2. Check logs:
   ```bash
   docker logs cloud-vault-mcp
   ```

3. Verify Docker is running:
   ```bash
   docker ps
   ```

### Authentication Failures

**Problem**: Client receives 401 Unauthorized.

**Solutions**:
1. Verify API key is correct:
   ```bash
   grep MCP_API_KEY .env
   ```

2. Check Authorization header format:
   ```
   Authorization: Bearer <key>
   ```
   NOT `Token <key>` or just `<key>`.

3. Regenerate API key if needed:
   ```bash
   python3 -c "import hashlib, os; print(hashlib.sha256(os.urandom(32)).hexdigest())"
   ```
   Update `.env` and restart server.

### Vault File Permission Issues

**Problem**: Server can't read/write vault files.

**Solutions**:
1. Check vault directory ownership:
   ```bash
   ls -la cloud-vault-mcp/vault
   ```

2. For Docker deployment, ensure volume has correct permissions:
   ```bash
   docker exec cloud-vault-mcp ls -la /vault
   ```

3. For local development, ensure `VAULT_PATH` is writable:
   ```bash
   touch $VAULT_PATH/test.md && rm $VAULT_PATH/test.md
   ```

### Git Sync Not Working

**Problem**: Changes aren't being committed or pushed.

**Solutions**:
1. Check git-sync container logs:
   ```bash
   docker logs cloud-vault-git-sync
   ```

2. Verify vault is a Git repo:
   ```bash
   cd cloud-vault-mcp/vault && git status
   ```

3. If using remote sync, verify `GIT_REMOTE_URL` is set in `.env`.

4. Check Git credentials are configured:
   ```bash
   docker exec cloud-vault-git-sync git config --list
   ```

### MCP Tools Not Appearing in Claude Code

**Problem**: Claude Code doesn't see the MCP server's tools.

**Solutions**:
1. Verify MCP config location:
   - Global: `~/.claude/mcp.json`
   - Project: `.mcp.json` in project root

2. Check JSON syntax is valid:
   ```bash
   python3 -m json.tool ~/.claude/mcp.json
   ```

3. Restart Claude Code after config changes.

4. Test MCP endpoint directly:
   ```bash
   curl -H "Authorization: Bearer <API_KEY>" \
        http://localhost:8360/mcp/tools/list
   ```

### Connection Timeouts

**Problem**: Client requests hang or timeout.

**Solutions**:
1. Check server is reachable:
   ```bash
   curl -I http://localhost:8360/health
   ```

2. For Docker, verify container is running:
   ```bash
   docker ps | grep cloud-vault
   ```

3. Check firewall/network settings if connecting from external host.

4. Increase client timeout if processing large vault operations.

## Security Considerations

### API Key Management

1. **Never commit API keys to Git**:
   - `.env` is in `.gitignore`
   - Use environment variables for client configuration

2. **Rotate keys periodically**:
   - Generate new key with provided Python command
   - Update `.env` and client configs
   - Restart server

3. **Use secure key generation**:
   ```bash
   python3 -c "import hashlib, os; print(hashlib.sha256(os.urandom(32)).hexdigest())"
   ```
   Don't use weak passwords or predictable values.

### Network Security

1. **Use HTTPS in production**:
   - Configure nginx with TLS certificates
   - Store certs in `deploy/nginx/certs/`
   - Start nginx: `docker compose up -d nginx`

2. **Restrict CORS origins**:
   ```bash
   # In .env
   CORS_ORIGINS=https://your-claude-instance.com,https://trusted-client.com
   ```

3. **Use firewall rules**:
   - Only expose port 8360 (or 443 for nginx) to trusted networks
   - For local development, bind to `127.0.0.1` only

### Vault Content Security

1. **Sensitive data in vault**:
   - Avoid storing credentials, API keys, or secrets in vault notes
   - Use `.gitignore` patterns for sensitive files
   - Consider encrypting sensitive notes with git-crypt

2. **Git remote authentication**:
   - Use SSH keys for Git remote URL
   - Don't embed credentials in `GIT_REMOTE_URL`
   - Configure Git credential store separately

3. **Docker volume permissions**:
   - Vault data volume is persistent across container restarts
   - Backup vault data regularly:
     ```bash
     docker run --rm -v cloud-vault-mcp_vault-data:/vault -v $(pwd)/backup:/backup alpine tar czf /backup/vault-backup.tar.gz /vault
     ```

## Advanced Usage

### Custom Templates

Add custom templates to vault directories:

1. Create `vault/<category>/_template.md`
2. Use `{{variable}}` syntax for placeholders
3. Call `vault_create_from_template` with template name and variables

### Git Integration

The vault is a Git repository. All changes are tracked:

```bash
# View commit history
cd cloud-vault-mcp/vault
git log --oneline

# Manual commit
git add -A
git commit -m "Manual update"

# Push to remote
git push origin main
```

Auto-sync commits every 5 minutes (configurable via `GIT_SYNC_INTERVAL`).

### Obsidian Desktop Integration

Open the vault in Obsidian for visual editing:

1. Open Obsidian
2. "Open folder as vault"
3. Select `cloud-vault-mcp/vault/`
4. Changes sync via Git (pull before editing, commit after)

### Scaling and Performance

For large vaults (>10,000 notes):

1. **Use folder-scoped search**:
   ```python
   vault_client.vault_search(query='term', scope='folder', folder='decisions')
   ```

2. **Enable Git shallow clones** for faster sync:
   ```bash
   git clone --depth 1 <remote_url>
   ```

3. **Consider separate vaults per project**:
   - Run multiple MCP servers on different ports
   - Each with its own vault and API key

4. **Use indexing for full-text search** (future enhancement):
   - Whoosh or Elasticsearch integration
   - Pre-build search index for faster queries

## Next Steps

1. **Wire MCP client to cohezion core** (Task #3, #4)
2. **Add integration tests** (Task #5)
3. **Use vault for compound engineering**:
   - Log decisions during agent execution
   - Extract patterns from successful workflows
   - Query prior context before new tasks
4. **Set up production deployment**:
   - Configure nginx with TLS
   - Set up Git remote for vault backup
   - Add monitoring and alerts

## References

- [MCP Protocol Specification](https://modelcontextprotocol.io/)
- [FastMCP Documentation](https://github.com/jlowin/fastmcp)
- [Obsidian](https://obsidian.md/)
- Cloud Vault source: `/home/mike-anderson/dev/cohezion/cloud-vault-mcp/`
