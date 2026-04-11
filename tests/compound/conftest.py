"""Fixtures for compound integration tests."""

import pytest
import pytest_asyncio
from unittest.mock import MagicMock

from cohezion.core.mcp_client import MCPClient


@pytest_asyncio.fixture
async def mcp_client():
    """Create mock MCP client for testing."""
    return MagicMock(spec=MCPClient)
