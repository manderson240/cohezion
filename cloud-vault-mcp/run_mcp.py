#!/usr/bin/env python3
"""Launcher for the cloud-vault MCP server.

Secrets (MCP_API_KEY, SURREALDB_PASS) are loaded from a gitignored ``.env`` next to
this file or from the existing environment — NEVER hardcoded. The previously committed
MCP_API_KEY is in git history and is therefore COMPROMISED: rotate it and put the new
value in ``cloud-vault-mcp/.env`` (see ``.env.example``).
"""

import os
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent


def _load_env_file(path: Path) -> None:
    """Load ``KEY=VALUE`` lines from a gitignored .env into os.environ (existing env wins)."""
    if not path.exists():
        return
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))


_load_env_file(_HERE / ".env")

# Non-secret config — safe to embed. ``setdefault`` so a real env/.env value wins.
os.environ.setdefault("VAULT_PATH", "/home/mike-anderson/vaults/cohezion-vault")
os.environ.setdefault("MCP_PORT", "8360")
os.environ.setdefault("SURREALDB_URL", "http://localhost:8001")
os.environ.setdefault("SURREALDB_USER", "root")
os.environ.setdefault("WATCHER_ENABLED", "false")  # Disable watcher (FastMCP ASGI workaround)

# Secrets MUST come from the environment or the gitignored .env — never hardcoded.
_missing = [k for k in ("MCP_API_KEY", "SURREALDB_PASS") if not os.environ.get(k)]
if _missing:
    sys.exit(
        "Missing required secret(s): "
        + ", ".join(_missing)
        + "\nSet them in cloud-vault-mcp/.env (gitignored) or the environment. "
        "Rotate MCP_API_KEY — the previously committed value is compromised."
    )

# Add current directory to path
sys.path.insert(0, str(_HERE))

# Import and run main
from src.mcp_server.main import main


main()
