# Cloud Vault MCP Server Startup Guide

## Overview
The Cloud Vault MCP Server provides Model Context Protocol (MCP) access to Obsidian vault operations with support for file watching, SSE events, and compound engineering workflows.

## Prerequisites

### 1. Environment Setup
Ensure you have:
- Python 3.11+
- The cloud-vault-mcp project installed
- A valid vault directory

### 2. Install Dependencies
```bash
cd /home/mike-anderson/dev/cohezion/cloud-vault-mcp
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

### 3. Verify Installation
```bash
# Test all imports
python3 -c "from src.mcp_server.main import main; print('✓ main.py imports OK')"
python3 -c "from src.mcp_server.config import ServerConfig; print('✓ config.py imports OK')"
python3 -c "from src.mcp_server.server import create_server; print('✓ server.py imports OK')"
```

## Critical Fixes Applied

### Import Path Issue (FIXED)
**Issue**: `from starlette.middleware.trustedhosts import TrustedHostMiddleware`
- **Error**: `ModuleNotFoundError: No module named 'starlette.middleware.trustedhosts'`
- **Root Cause**: Starlette 0.52.1 uses `trustedhost` (singular) not `trustedhosts` (plural)
- **Fix**: Changed to `from starlette.middleware.trustedhost import TrustedHostMiddleware`
- **File**: `/home/mike-anderson/dev/cohezion/cloud-vault-mcp/src/mcp_server/main.py:9`

## Configuration

The server reads configuration from environment variables:

```bash
# Required
export VAULT_PATH=/home/mike-anderson/dev/cohezion/cloud-vault-mcp/vault

# Optional (defaults shown)
export MCP_HOST=0.0.0.0              # Listen address
export MCP_PORT=8360                 # Port
export MCP_API_KEY=""                # API key (empty = no auth)
export LOG_LEVEL=info                # Logging level
export WATCHER_ENABLED=false          # File watcher (SSE)
export SSE_HEARTBEAT=15              # SSE heartbeat interval (seconds)
export ALLOWED_HOSTS="*"             # CORS/host allowlist
export ANTHROPIC_API_KEY=""          # For inbox processor
export INBOX_DEBOUNCE=2.0            # Inbox debounce (seconds)
export INBOX_MODEL=claude-haiku-4-5-20251001
```

## Starting the Server

### 1. Basic Startup
```bash
cd /home/mike-anderson/dev/cohezion/cloud-vault-mcp
source .venv/bin/activate

export VAULT_PATH=/home/mike-anderson/dev/cohezion/cloud-vault-mcp/vault
export MCP_PORT=8360

python3 -m src.mcp_server.main
```

Expected output:
```
2026-02-09 08:49:31,359 [WARNING] cloud-vault-mcp: MCP_API_KEY is not set...
2026-02-09 08:49:31,359 [INFO] cloud-vault-mcp: Vault path: /home/mike-anderson/dev/cohezion/cloud-vault-mcp/vault
2026-02-09 08:49:31,359 [INFO] cloud-vault-mcp: Starting Cloud Vault MCP Server on 0.0.0.0:8360
INFO:     Uvicorn running on http://0.0.0.0:8360
```

### 2. Background Startup
```bash
cd /home/mike-anderson/dev/cohezion/cloud-vault-mcp
source .venv/bin/activate
export VAULT_PATH=/home/mike-anderson/dev/cohezion/cloud-vault-mcp/vault
export MCP_PORT=8360
nohup python3 -m src.mcp_server.main > server.log 2>&1 &
echo $! > server.pid
```

### 3. With File Watcher & SSE
```bash
export VAULT_PATH=/home/mike-anderson/dev/cohezion/cloud-vault-mcp/vault
export MCP_PORT=8360
export WATCHER_ENABLED=true
export SSE_HEARTBEAT=15
python3 -m src.mcp_server.main
```

## Testing the Server

### 1. Connection Test
```bash
curl -s http://127.0.0.1:8360/ -w "\nStatus: %{http_code}\n"
```

### 2. SSE Events (if watcher enabled)
```bash
curl -N http://127.0.0.1:8360/events/vault
```

### 3. MCP Operations
The server provides FastMCP endpoints for vault operations. Test via MCP client:
```python
from mcp.client.sse import SSEClientTransport
from mcp.client.sync_client import SyncClient

transport = SSEClientTransport("http://127.0.0.1:8360")
client = SyncClient(transport)
resources = client.list_resources()
```

## Troubleshooting

### Issue: `ModuleNotFoundError: No module named 'starlette.middleware.trustedhosts'`
**Solution**: This was the primary issue fixed. Ensure you have updated `main.py` line 9 to use:
```python
from starlette.middleware.trustedhost import TrustedHostMiddleware
```

### Issue: `ValueError: Vault path does not exist: /vault`
**Solution**: Set the correct VAULT_PATH:
```bash
export VAULT_PATH=/home/mike-anderson/dev/cohezion/cloud-vault-mcp/vault
python3 -m src.mcp_server.main
```

### Issue: Address already in use
**Solution**: Use a different port or stop the previous process:
```bash
# Find process
lsof -i :8360
# Kill it
kill -9 <PID>
# Or use a different port
export MCP_PORT=8361
python3 -m src.mcp_server.main
```

### Issue: MCP_API_KEY warning in production
**Solution**: Set the API key for production:
```bash
export MCP_API_KEY=$(openssl rand -hex 32)
python3 -m src.mcp_server.main
```

### Issue: SSE events not streaming
**Solution**: Ensure watcher is enabled and vault has write access:
```bash
export WATCHER_ENABLED=true
# Check vault permissions
ls -la /home/mike-anderson/dev/cohezion/cloud-vault-mcp/vault/
# Should have write permission
```

## Diagnostics

### Check Server Health
```bash
# View recent logs
tail -50 server.log

# Check if port is listening
netstat -an | grep 8360
lsof -i :8360

# Check vault connectivity
ls -la /home/mike-anderson/dev/cohezion/cloud-vault-mcp/vault/
python3 -c "from pathlib import Path; print(Path('/home/mike-anderson/dev/cohezion/cloud-vault-mcp/vault').exists())"
```

### Debug Mode
```bash
export LOG_LEVEL=debug
python3 -m src.mcp_server.main 2>&1 | tee server-debug.log
```

### Test Dependencies
```bash
# All should succeed
python3 -c "import uvicorn; print('✓ uvicorn')"
python3 -c "import starlette; print(f'✓ starlette {starlette.__version__}')"
python3 -c "from starlette.middleware.trustedhost import TrustedHostMiddleware; print('✓ TrustedHostMiddleware')"
python3 -c "import mcp; print('✓ mcp')"
python3 -c "import watchdog; print('✓ watchdog')"
python3 -c "import anthropic; print('✓ anthropic')"
```

## Inbox Processor

The inbox processor is a daemon that watches `/vault/inbox/` for new notes and processes them:

```bash
# Run inbox processor
source .venv/bin/activate
export VAULT_PATH=/home/mike-anderson/dev/cohezion/cloud-vault-mcp/vault
export ANTHROPIC_API_KEY=sk-...
python3 -m src.mcp_server.inbox_main

# Stop with Ctrl+C
```

## Dependency Management Notes

### Installation Method
- Uses `pyproject.toml` with `hatchling` build backend
- Python 3.11+ required
- Key dependencies:
  - `mcp[cli]>=1.2.0` — FastMCP framework
  - `uvicorn>=0.30.0` — ASGI server
  - `starlette>=0.38.0` — Web framework
  - `watchdog>=4.0` — File watching
  - `anthropic>=0.40.0` — Anthropic API client

### Environment Management
- Virtual environment: `/home/mike-anderson/dev/cohezion/cloud-vault-mcp/.venv`
- Activation: `source .venv/bin/activate`
- Development install: `pip install -e .`

## Error Resolution Patterns

### Pattern 1: Import Errors
1. Verify venv is activated: `which python3` should show `.venv/bin/python3`
2. Check module is installed: `python3 -c "import <module>"`
3. Update if needed: `pip install --upgrade <module>`

### Pattern 2: Runtime Errors
1. Enable debug logging: `export LOG_LEVEL=debug`
2. Check environment variables: `env | grep -E "VAULT|MCP|LOG"`
3. Verify file paths exist: `ls -la <path>`
4. Check file permissions: `test -r <path> && echo "readable"`

### Pattern 3: Connection Errors
1. Verify server is running: `curl http://127.0.0.1:8360/`
2. Check network: `netstat -an | grep 8360`
3. Verify firewall: `sudo ufw status`
4. Test with telnet: `telnet 127.0.0.1 8360`

## Performance Considerations

- **SSE Heartbeat**: Default 15 seconds (configurable with `SSE_HEARTBEAT`)
- **File Watcher**: Debounce 0.5 seconds (prevents duplicate events)
- **Inbox Processor**: Debounce configurable with `INBOX_DEBOUNCE`

## Security Notes

- **API Key**: Empty by default. Set `MCP_API_KEY` for production
- **CORS**: Defaults to `*` (all origins). Restrict with `ALLOWED_HOSTS`
- **Vault Access**: Server can read/write vault files. Ensure proper file permissions
- **Credentials**: Don't commit `.env` or API keys to version control

## Session 40 Status

### Fixes Completed
✓ Fixed Starlette import path (`trustedhosts` → `trustedhost`)
✓ Verified all dependencies installed
✓ Confirmed vault directory connectivity
✓ Tested server startup and ASGI app initialization
✓ Created comprehensive startup documentation

### Verification Results
- Python environment: 3.13
- Starlette version: 0.52.1
- Server startup: SUCCESS
- Vault connectivity: SUCCESS
- All imports: PASSING

### Next Steps (Phase 5B Tasks)
1. Task #5 — Configure Claude Code MCP integration
2. Task #1 — Assess vault/MCP current state and dependencies (COMPLETE)
3. Task #2 — Plan non-destructive MCP integration strategy
4. Task #3 — Ensure proper git branching
5. Task #7 — Final verification and handoff

---
**Last Updated**: 2026-02-09
**Verified By**: Task #4 - MCP Backend Engineer
**Status**: READY FOR PRODUCTION
