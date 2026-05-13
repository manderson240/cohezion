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


def get_bmad_data_path() -> Path:
    """Get BMAD data path."""
    return Path(os.getenv("BMAD_DATA_PATH", "_bmad"))


def get_redis_url() -> str:
    """Get Redis URL."""
    return get_credentials().get_secret("COHEZION_REDIS_URL", env_var="REDIS_URL") or "redis://localhost:6379"


_engine: BMADEngine | None = None
_session_manager: SessionManager | None = None


def get_engine() -> BMADEngine:
    """Get or create BMAD engine."""
    global _engine
    if _engine is None:
        data_path = get_bmad_data_path()
        _engine = BMADEngine(data_path)
        logger.info(f"BMAD engine initialized with data from {data_path}")
    return _engine


def get_session_manager() -> SessionManager:
    """Get or create session manager."""
    global _session_manager
    if _session_manager is None:
        redis_url = get_redis_url()
        _session_manager = SessionManager(redis_url)
        logger.info(f"Session manager initialized with Redis at {redis_url}")
    return _session_manager
