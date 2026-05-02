"""Fixtures for compound integration tests."""

from unittest.mock import MagicMock

import pytest_asyncio

from cohezion.core.mcp_client import MCPClient


@pytest_asyncio.fixture
async def mcp_client():
    """Create mock MCP client for testing."""
    return MagicMock(spec=MCPClient)
