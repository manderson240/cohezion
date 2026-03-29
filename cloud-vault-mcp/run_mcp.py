#!/usr/bin/env python3
import os
import sys


# Set environment variables
os.environ["VAULT_PATH"] = "/home/mike-anderson/vaults/cohezion-vault"
os.environ["MCP_PORT"] = "8360"
os.environ["SURREALDB_URL"] = "http://localhost:8001"
os.environ["SURREALDB_USER"] = "root"
os.environ["SURREALDB_PASS"] = "root"
os.environ["MCP_API_KEY"] = (
    "a712027605bbd33068da5462bbcc18d90f844df23f948f124908fa726d678263"
)
os.environ["WATCHER_ENABLED"] = (
    "false"  # Disable watcher to work around FastMCP ASGI issue
)

# Add current directory to path
sys.path.insert(0, "/home/mike-anderson/dev/cohezion/cloud-vault-mcp")

# Import and run main
from src.mcp_server.main import main


main()
