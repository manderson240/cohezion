#!/usr/bin/env python3
import os
import sys


# Set environment variables
os.environ["VAULT_PATH"] = "/home/mike-anderson/vaults/cohezion-vault"
os.environ["MCP_PORT"] = "8360"
os.environ["SURREALDB_URL"] = "http://localhost:8001"
os.environ["SURREALDB_USER"] = "root"
os.environ["SURREALDB_PASS"] = "root"
# MCP_API_KEY is NOT set here: it comes from the environment (cohezion-vault.service sets
# it; move it to a 0600 EnvironmentFile). The server refuses to start without one. A
# literal here was tracked in git and overrode the unit's value unconditionally.
os.environ["WATCHER_ENABLED"] = (
    "false"  # Disable watcher to work around FastMCP ASGI issue
)

# Add current directory to path
sys.path.insert(0, "/home/mike-anderson/dev/cohezion/cloud-vault-mcp")

# Import and run main
from src.mcp_server.main import main


main()
