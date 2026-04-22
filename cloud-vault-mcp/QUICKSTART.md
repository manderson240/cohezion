# Cloud Vault MCP Server - Quick Start Guide

## 5-Minute Setup

### 1. Start the Server

```bash
cd /home/mike-anderson/dev/cohezion/cloud-vault-mcp
./setup.sh
```

Save the API key displayed during setup.

### 2. Verify Server is Running

```bash
curl http://localhost:8360/health
```

Expected: `{"status":"ok"}`

### 3. Configure Claude Code

Add to `~/.claude/mcp.json` (create if doesn't exist):

```json
{
  "mcpServers": {
    "cloud-vault": {
      "type": "streamable-http",
      "url": "http://localhost:8360/mcp",
      "headers": {
        "Authorization": "Bearer <YOUR_API_KEY_FROM_STEP_1>"
      }
    }
  }
}
```

### 4. Test from Command Line

```bash
# Set your API key
export API_KEY="<your-key-from-step-1>"

# Test vault read
curl -X POST http://localhost:8360/mcp/tools/call \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "tool": "vault_list",
    "arguments": {"directory": "", "recursive": false}
  }'

# Test vault search
curl -X POST http://localhost:8360/mcp/tools/call \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "tool": "vault_search",
    "arguments": {"query": "compound", "scope": "all"}
  }'
```

### 5. Use from Python

```python
import requests

API_KEY = '<your-key>'
BASE_URL = 'http://localhost:8360'

def call_tool(tool_name, **kwargs):
    response = requests.post(
        f'{BASE_URL}/mcp/tools/call',
        headers={'Authorization': f'Bearer {API_KEY}'},
        json={'tool': tool_name, 'arguments': kwargs}
    )
    return response.json()

# Log a decision
result = call_tool(
    'vault_log_decision',
    project='test',
    title='My First Decision',
    context='Testing the MCP server',
    decision='Use the MCP server for knowledge management',
    rationale='It provides structured, searchable, version-controlled notes'
)

print(result)
# Output: "Created decision: decisions/test/2026-02-07-my-first-decision.md"

# Read it back
content = call_tool('vault_read', path='decisions/test/2026-02-07-my-first-decision.md')
print(content)
```

## Common Operations

### Log an Architecture Decision

```python
call_tool(
    'vault_log_decision',
    project='cohezion',
    title='Use SurrealDB for Agent State',
    context='Need persistent storage for agent journey data',
    decision='Use SurrealDB with JSONL fallback',
    rationale='Graph queries for relationships, JSONL for resilience',
    alternatives_considered='PostgreSQL (no graph), Neo4j (complex setup)'
)
```

### Log an Experiment

```python
call_tool(
    'vault_log_experiment',
    project='cohezion',
    hypothesis='Batch caching will reduce token costs by 80%',
    method='Implemented SHA-256 hash-based cache, ran 10 cycles',
    result='98% hit rate, reduced cost from 2.5M to 50K tokens',
    learnings='Hash caching works for deterministic prompts'
)
```

### Search for Prior Context

```python
results = call_tool(
    'vault_find_relevant_context',
    query='token efficiency caching',
    project='cohezion'
)
print(results)
```

### Extract a Pattern

```python
call_tool(
    'vault_extract_pattern',
    source_path='projects/cohezion/phase-6.md',
    pattern_name='Non-Critical Observability',
    description='Wrap observability features in try/except so they never break execution',
    code_example='try:\n    tracker.record()\nexcept Exception:\n    logger.debug("non-critical")',
    domain='observability'
)
```

## Troubleshooting

### Can't connect to server

```bash
# Check if running
docker ps | grep cloud-vault

# Check logs
docker logs cloud-vault-mcp

# Restart
docker compose restart mcp-server
```

### 401 Unauthorized

- Check API key matches: `grep MCP_API_KEY .env`
- Verify header format: `Authorization: Bearer <key>`

### Vault file errors

```bash
# Check vault directory
ls -la vault/

# Re-initialize if needed
cd vault && git status
```

## Next Steps

- Read full documentation: `/home/mike-anderson/dev/cohezion/docs/mcp-integration.md`
- Explore vault structure: `ls -R vault/`
- Open vault in Obsidian for visual editing
- Set up Git remote for backup
- Integrate with cohezion compound workflows

## Server Commands

```bash
# Start
docker compose up -d mcp-server

# Stop
docker compose stop mcp-server

# View logs
docker logs -f cloud-vault-mcp

# Restart
docker compose restart mcp-server

# Rebuild after code changes
docker compose build mcp-server
docker compose up -d mcp-server
```

## Development Mode

For local Python development:

```bash
./setup.sh --dev

export VAULT_PATH=$(pwd)/vault
source .env
export MCP_API_KEY MCP_PORT

# Run directly
python -m mcp_server.main

# Or use installed command
cloud-vault-mcp
```

## Available Tools

Quick reference of MCP tools:

**Core Operations:**
- `vault_read`, `vault_write`, `vault_edit`, `vault_delete`
- `vault_list`, `vault_search`

**Obsidian Features:**
- `vault_backlinks`, `vault_forward_links`, `vault_tags`
- `vault_create_from_template`

**Compound Engineering:**
- `vault_log_decision`, `vault_log_experiment`, `vault_extract_pattern`
- `vault_find_relevant_context`

See full documentation for parameters and examples.
