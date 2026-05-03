"""Fixtures for compound integration tests."""

from unittest.mock import MagicMock, patch

import pytest
import pytest_asyncio

from cohezion.core.mcp_client import MCPClient


class _MockVirtualMemory:
    """Fake psutil result — reports 50% memory so resource guardrails don't fire."""
    percent = 50.0


@pytest.fixture(autouse=True)
def _mock_psutil_memory():
    """Auto-patch psutil.virtual_memory for all compound tests.

    The resource guardrail in CompoundExecutor blocks execution when system
    memory exceeds ~85%. On a busy machine (running the EVO loop, etc.) real
    memory can be 90%+, causing every test that calls execute_task to fail.
    Mocking at conftest level fixes this suite-wide without touching each test.
    """
    with patch("psutil.virtual_memory", return_value=_MockVirtualMemory()):
        yield


@pytest_asyncio.fixture
async def mcp_client():
    """Create mock MCP client for testing."""
    return MagicMock(spec=MCPClient)
