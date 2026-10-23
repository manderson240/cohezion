#!/usr/bin/env python3
"""Local launcher for the cohezion vault MCP server.

All configuration comes from the environment. ``MCP_API_KEY`` is required by the
server itself (``src/mcp_server/main.py`` refuses to start without it) and is never
stored in this file: an earlier revision carried the key as a literal, and that
literal is in the public repository history. Any key that was ever committed must
be treated as compromised and rotated.
"""

import os
import sys
from pathlib import Path


_HERE = Path(__file__).resolve().parent

os.environ.setdefault("VAULT_PATH", str(Path.home() / "vaults" / "cohezion-vault"))
os.environ.setdefault("MCP_PORT", "8360")
os.environ.setdefault("SURREALDB_URL", "http://localhost:8001")
# Disable the watcher to work around the FastMCP ASGI issue.
os.environ.setdefault("WATCHER_ENABLED", "false")

sys.path.insert(0, str(_HERE))

from src.mcp_server.main import main  # noqa: E402


main()
