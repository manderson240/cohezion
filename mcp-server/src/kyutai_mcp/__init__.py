"""Kyutai MCP Server - Voice AI integration for Obsidian."""

__version__ = "0.1.0"
__author__ = "Kyutai Team"

from .config import KyutaiMCPConfig
from .server import create_server

__all__ = [
    "KyutaiMCPConfig",
    "create_server",
]
