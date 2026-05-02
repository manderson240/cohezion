"""BMAD MCP Server - FastMCP app, config, and engine accessors."""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

from fastmcp import FastMCP

from cohezion.mcp.servers.bmad.engine import BMADEngine
from cohezion.mcp.shared.session import SessionManager
from cohezion.security.credentials import get_credentials


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("bmad-mcp")

app = FastMCP("bmad-method")

BMAD_DATA_PATH = Path(os.getenv("BMAD_DATA_PATH", "_bmad"))
REDIS_URL = get_credentials().get_secret("COHEZION_REDIS_URL", env_var="REDIS_URL") or "redis://localhost:6379"

_engine: BMADEngine | None = None
_session_manager: SessionManager | None = None


def get_engine() -> BMADEngine:
    """Get or create BMAD engine."""
    global _engine
    if _engine is None:
        _engine = BMADEngine(BMAD_DATA_PATH)
        logger.info(f"BMAD engine initialized with data from {BMAD_DATA_PATH}")
    return _engine


def get_session_manager() -> SessionManager:
    """Get or create session manager."""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager(REDIS_URL)
        logger.info(f"Session manager initialized with Redis at {REDIS_URL}")
    return _session_manager
