# Fix SessionStart MCP Health Check Warning

## Context

The `mcp-health-check.sh` SessionStart hook is reporting a warning:
```
[mcp-health-check] Warning: 1 service(s) unreachable:
  - cohezion-vault (http://localhost:8360)
```

This is NOT an error - it's a warning that the vault service isn't running. However, the user expects `cohezion-vault` to start automatically as part of the MCP fleet when running `wake_up.py`.

## Root Cause Analysis

**Location of health check:** `.claude/hooks/mcp-health-check.sh`
- Checks three services: cohezion-vault (8360), surrealdb (8000), ollama (11434)
- SurrealDB and Ollama are expected to be started externally
- cohezion-vault should be started by the MCP server manager

**Location of server registration:** `src/cohezion/mcp/manager/defaults.py`
- `init_default_servers()` registers 12 MCP servers (bmad, skills, doc-retriever, huggingface, memory, sequential-thinking, git-context, security, knowledge, swarm, research)
- **Missing:** `cohezion-vault` on port 8360

**The cloud-vault-mcp server:**
- Located in `cloud-vault-mcp/` directory with its own package (`mcp_server`)
- Entry point: `cloud-vault-mcp` command (defined in its `pyproject.toml`)
- Runs on port 8360 (configurable via `MCP_PORT` env var)
- Default vault path: `/vault` (configurable via `VAULT_PATH` env var)
- Health endpoint: `/health` returns 200 when healthy

**The server_manager launcher** (`src/cohezion/mcp/manager/server_manager.py` lines 107-118):
- Expects entry points in format `module.path:app_object`
- Runs: `python -m <module_path>` where module_path is the part before `:`
- Sets `MCP_PORT` env var before starting
- Cloud-vault-mcp exports `main()` function, not an `app` object

## Implementation Plan

### Step 1: Add cloud-vault-mcp as editable dependency
**File:** `pyproject.toml`

Add cloud-vault-mcp as a local editable dependency so it's importable:
```toml
dependencies = [
    # ... existing deps ...
    "cloud-vault-mcp",
]

[tool.uv.sources]
cloud-vault-mcp = { path = "cloud-vault-mcp", editable = true }
```

### Step 2: Create vault server wrapper
**File:** `src/cohezion/mcp/servers/vault/__init__.py` (new file)

Create a minimal wrapper module that imports and runs the cloud-vault-mcp:
```python
"""Vault MCP Server wrapper."""
import os
import sys

# Ensure cloud-vault-mcp is importable
try:
    from mcp_server.main import main
except ImportError:
    # Add cloud-vault-mcp src to path if not installed
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "cloud-vault-mcp", "src"))
    from mcp_server.main import main

def run_server():
    """Entry point for server manager."""
    main()

if __name__ == "__main__":
    run_server()
```

### Step 3: Register vault server in defaults
**File:** `src/cohezion/mcp/manager/defaults.py`

Add vault server registration in `init_default_servers()`:
```python
# Register Vault MCP Server (Port 8360)
manager.register_server(
    name="vault",
    entry_point="cohezion.mcp.servers.vault:run_server",
    preferred_port=8360,
    auto_restart=True,
    env_vars={
        "VAULT_PATH": os.environ.get("VAULT_PATH", "/vault"),
        "MCP_API_KEY": os.environ.get("MCP_API_KEY", ""),
        "LOG_LEVEL": "INFO",
        "WATCHER_ENABLED": "true",
        "HEALTH_CHECK_ENABLED": "true",
    },
)
```

### Step 4: Verification

After implementing:
1. Run `uv pip install -e .` to install the editable dependency
2. Run `uv run python scripts/wake_up.py` to start all MCP servers
3. Check `curl http://localhost:8360/health` returns 200
4. The SessionStart hook should no longer show the vault warning

## Critical Files

| File | Action | Lines |
|------|--------|-------|
| `pyproject.toml` | Add dependency + source | ~34 deps section, add [tool.uv.sources] |
| `src/cohezion/mcp/servers/vault/__init__.py` | Create new | New file (~20 lines) |
| `src/cohezion/mcp/manager/defaults.py` | Add registration | After line 143, before logger.info |

## Testing

1. Install: `uv pip install -e .`
2. Start fleet: `uv run python scripts/wake_up.py`
3. Check health: `curl -s http://localhost:8360/health | jq .`
4. Verify no warning on new session start
