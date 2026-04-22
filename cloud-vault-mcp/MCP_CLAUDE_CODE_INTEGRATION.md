# Cloud Vault MCP - Claude Code Integration Guide

## Overview

The Cloud Vault MCP Server integrates with Claude Code, enabling knowledge vault access directly from your AI coding sessions. This document provides configuration, testing, and troubleshooting guidance.

## Architecture

```
Claude Code Agent
    ↓
~/.claude/mcp.json (HTTP transport configuration)
    ↓
Cloud Vault MCP Server (localhost:8360)
    ↓
Vault Directory (/home/mike-anderson/vaults/cohezion-vault)
```

## Configuration

### 1. Claude Code MCP Configuration File

**Location**: `~/.claude/mcp.json`

**Current Configuration**:
```json
{
  "cloud-vault-mcp": {
    "type": "http",
    "url": "http://127.0.0.1:8360",
    "headers": {
      "Authorization": "Bearer a712027605bbd33068da5462bbcc18d90f844df23f948f124908fa726d678263"
    }
  }
}
```

**Configuration Fields**:
- `type`: Protocol type - `"http"` for HTTP transport (standard for local dev)
- `url`: Server endpoint - `http://127.0.0.1:8360` (adjust port if needed)
- `headers`: HTTP headers for authentication
  - `Authorization`: Bearer token matching `MCP_API_KEY` from server `.env`

### 2. Environment Variables for MCP Server

The server reads configuration from environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `VAULT_PATH` | `/vault` | Path to vault directory |
| `MCP_PORT` | `8360` | HTTP server port |
| `MCP_API_KEY` | (required) | Bearer token for auth header |
| `MCP_HOST` | `0.0.0.0` | Bind address |
| `CORS_ORIGINS` | `*` | CORS allowed origins |
| `LOG_LEVEL` | `info` | Logging level |
| `WATCHER_ENABLED` | `true` | Enable file watcher for vault changes |

**Production Startup**:
```bash
export VAULT_PATH=/home/mike-anderson/vaults/cohezion-vault
export MCP_PORT=8360
export MCP_API_KEY=a712027605bbd33068da5462bbcc18d90f844df23f948f124908fa726d678263

cd /home/mike-anderson/dev/cohezion/cloud-vault-mcp
uv run python -m src.mcp_server.main
```

## Available MCP Tools

### Core Vault Operations

#### `vault_read`
Read a note's content from the vault.

```
Args:
  path (str): File path within vault (e.g., 'decisions/2026-02-09-my-decision.md')

Returns:
  str: File content
```

#### `vault_search`
Search vault notes by keyword.

```
Args:
  query (str): Search keyword or phrase
  max_results (int, optional): Maximum results (default: 10)

Returns:
  str: JSON-formatted search results with paths and snippets
```

#### `vault_list`
List all notes in vault or within a specific directory.

```
Args:
  path (str, optional): Directory path within vault (default: root)

Returns:
  str: JSON-formatted list of notes with metadata
```

#### `vault_write`
Write or update a note in the vault.

```
Args:
  path (str): File path within vault
  content (str): File content
  create_dirs (bool, optional): Create parent directories if needed (default: true)

Returns:
  str: Success message or error details
```

### Compound Engineering Operations

#### `compound_record_decision`
Log a decision to the vault with standardized format.

```
Args:
  title (str): Decision title
  context (str): Problem context
  decision (str): The decision made
  reasoning (str): Why this decision was made
  tags (list[str], optional): Tags for categorization

Returns:
  str: Path to created decision file
```

#### `compound_record_experiment`
Log an experiment to the vault.

```
Args:
  title (str): Experiment title
  hypothesis (str): What you expect to happen
  procedure (str): Step-by-step procedure
  results (str): What actually happened
  insights (str): Key learnings

Returns:
  str: Path to created experiment file
```

#### `compound_record_pattern`
Document a reusable pattern or technique.

```
Args:
  name (str): Pattern name
  problem (str): Problem it solves
  solution (str): The pattern itself
  examples (str): Usage examples
  trade_offs (str): Pros and cons

Returns:
  str: Path to created pattern file
```

### Obsidian Integration

#### `obsidian_link_note`
Create a wikilink between notes.

```
Args:
  from_path (str): Source note path
  to_path (str): Target note path
  link_text (str, optional): Custom link text

Returns:
  str: Updated content of source note
```

#### `obsidian_get_backlinks`
Find all notes that link to a given note.

```
Args:
  path (str): Note path

Returns:
  str: JSON list of files that link to this note
```

## Quick Start

### 1. Start the MCP Server

```bash
# Terminal 1: Start MCP server
cd /home/mike-anderson/dev/cohezion/cloud-vault-mcp
VAULT_PATH=/home/mike-anderson/vaults/cohezion-vault \
MCP_PORT=8360 \
MCP_API_KEY=a712027605bbd33068da5462bbcc18d90f844df23f948f124908fa726d678263 \
uv run python -m src.mcp_server.main
```

**Expected Output**:
```
2026-02-09 09:00:00,123 [INFO] cloud-vault-mcp: Vault path: /home/mike-anderson/vaults/cohezion-vault
2026-02-09 09:00:00,124 [INFO] cloud-vault-mcp: Starting Cloud Vault MCP Server on 0.0.0.0:8360
INFO:     Started server process [12345]
INFO:     Application startup complete.
```

### 2. Verify Server Health

```bash
# Terminal 2: Check server health
curl http://localhost:8360/health

# Expected response: 200 OK (or "Internal Server Error" if route not implemented)
```

### 3. Test Claude Code Discovery

In Claude Code CLI, the MCP tools should be automatically discovered from `~/.claude/mcp.json`:

```bash
# Claude Code should list available tools
/mcp list

# Or query specific tool
/mcp info vault_read
```

### 4. Use Vault Tools in Claude Code

```
I need to search the vault for decisions about token optimization.
Use the vault_search tool to find relevant notes.

Then use vault_read to get the full content of the most relevant decision.
```

## Testing & Troubleshooting

### Health Check

```bash
curl -v http://localhost:8360/health
```

**Expected**: HTTP 200 or HTTP 500 (server started but route not implemented)
**Problem**: Connection refused → Server not running

### Test Tool Execution

#### From CLI (when server is running)

```bash
# Test vault_read tool
curl -X POST http://localhost:8360/call/vault_read \
  -H "Content-Type: application/json" \
  -d '{"path": "decisions/2026-02-09-high-coherence-achieved-with-token-optimization.md"}'
```

#### From Claude Code (once integrated)

```
Use the vault_read tool to read decisions/2026-02-09-high-coherence-achieved-with-token-optimization.md
```

### Common Issues

#### Issue: "Connection refused" on port 8360

**Cause**: MCP server not running

**Solution**:
1. Ensure server process is running: `ps aux | grep "mcp_server\|uvicorn"`
2. Check port: `lsof -i :8360`
3. Start server with proper environment variables
4. Check `/tmp/mcp_server.log` for startup errors

#### Issue: "Authorization failed" or 401 error

**Cause**: API key mismatch between `mcp.json` and server `.env`

**Solution**:
1. Check API key in `~/.claude/mcp.json`
2. Check API key in `/home/mike-anderson/dev/cohezion/cloud-vault-mcp/.env`
3. Restart server after updating `.env`: `pkill -f "mcp_server"; sleep 2; <start command>`

#### Issue: "Vault path does not exist"

**Cause**: VAULT_PATH environment variable points to wrong directory

**Solution**:
```bash
# Verify vault path exists
ls -ld /home/mike-anderson/vaults/cohezion-vault

# Update .env VAULT_PATH to correct location
export VAULT_PATH=/home/mike-anderson/vaults/cohezion-vault
```

#### Issue: "Starlette middleware import error"

**Cause**: Incorrect Starlette middleware import path

**Status**: FIXED in current version (`trustedhost` not `trustedhosts`)

**Solution**: Update `src/mcp_server/main.py` line 9:
```python
# Correct
from starlette.middleware.trustedhost import TrustedHostMiddleware

# Wrong (old)
from starlette.middleware.trustedhosts import TrustedHostMiddleware
```

## Integration with Claude Code Workflows

### Workflow: Record Decision from Coding Session

1. Claude Code encounters a design decision
2. Uses `compound_record_decision` tool to log it:
```
Title: "Implement token-efficient batch executor"
Context: "Needed 40% token reduction for compound engineering"
Decision: "Use semantic embeddings for query similarity"
Reasoning: "50x compression, still maintains query intent"
```
3. Decision persisted to vault for future reference
4. Other agents can search and build on previous decisions

### Workflow: Search and Context Building

1. New task requires understanding previous work
2. Claude Code searches vault: `vault_search("token optimization")`
3. Gets list of related decisions, experiments, patterns
4. Reads relevant ones with `vault_read`
5. Builds context for current task

### Workflow: Pattern Documentation

After successfully implementing a technique:
```
Use compound_record_pattern to document:
- Problem: How to efficiently cache large embeddings
- Solution: 3-tier cache (L1 hash, L2 cosine, L3 vault)
- Examples: <code snippet>
- Trade-offs: Speed vs memory vs persistence
```

## Security Considerations

### API Key Management

**Current Setup**: Bearer token in `mcp.json` (INSECURE for production)

```json
{
  "Authorization": "Bearer a712027605bbd33068da5462bbcc18d90f844df23f948f124908fa726d678263"
}
```

**Issues**:
- Token visible in plaintext config file
- No token rotation mechanism
- Shared across all users/sessions

**Production Improvements**:
1. Use environment variable: `Authorization: Bearer $MCP_API_KEY`
2. Implement token rotation with expiry
3. Use TLS/HTTPS instead of HTTP
4. Implement per-session tokens
5. Add request signing/HMAC validation

### Vault Access Control

**Current**: All authenticated users can access entire vault

**Production Improvements**:
1. Implement path-based access control
2. Role-based permissions (read, write, admin)
3. Audit logging for all vault operations
4. Encryption at rest for sensitive notes

## File Structure Reference

```
cloud-vault-mcp/
├── .env                          # Environment configuration
├── src/mcp_server/
│   ├── main.py                   # Server entry point
│   ├── server.py                 # FastMCP server definition + tools
│   ├── config.py                 # Configuration loading
│   ├── vault_ops.py              # Vault file operations
│   ├── compound_ops.py           # Compound engineering tools
│   ├── obsidian_ops.py           # Obsidian link management
│   ├── vault_watcher.py          # File system watcher
│   ├── memory_bridge.py          # Memory persistence bridge
│   └── sheets_bridge.py          # Google Sheets integration
└── pyproject.toml               # Package definition
```

## Maintenance

### Health Monitoring

Daily checks:
```bash
# Server running?
ps aux | grep "mcp_server\|uvicorn" | grep -v grep

# Port accessible?
curl -s http://localhost:8360/health

# Vault file integrity?
find /home/mike-anderson/vaults/cohezion-vault -name "*.md" | wc -l
```

### Log Management

```bash
# View recent logs
tail -100 /tmp/mcp_server.log

# Search for errors
grep "ERROR\|Traceback" /tmp/mcp_server.log

# Archive old logs
mv /tmp/mcp_server.log /tmp/mcp_server.log.$(date +%Y%m%d_%H%M%S)
```

### Updating Configuration

1. Edit `~/.claude/mcp.json` for Claude Code changes
2. Edit `.env` for server changes
3. Restart server: `pkill -f "mcp_server"; sleep 2; <start command>`
4. Restart Claude Code session to reload MCP tools

## References

- **MCP Specification**: https://modelcontextprotocol.io
- **FastMCP Documentation**: https://github.com/jlouns/fastmcp
- **Starlette Docs**: https://www.starlette.io/
- **Vault Location**: `/home/mike-anderson/vaults/cohezion-vault`
- **API Key**: `a712027605bbd33068da5462bbcc18d90f844df23f948f124908fa726d678263`

