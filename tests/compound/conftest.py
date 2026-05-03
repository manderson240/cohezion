"""Fixtures for compound integration tests."""

from unittest.mock import MagicMock, patch

import pytest
import pytest_asyncio

from cohezion.core.mcp_client import MCPClient


class _MockVirtualMemory:
    """Fake psutil result — reports 50% memory so resource guardrails don't fire.

    Includes all attributes used by silicon_guard.py, resource_monitor, and executor:
      - percent: used by executor guardrail (threshold ~85-90%)
      - total: 128 GiB (Strix Halo spec)
      - available: 64 GiB free
    """
    percent = 50.0
    total = 128 * 1024 ** 3   # 128 GiB
    available = 64 * 1024 ** 3  # 64 GiB free
    used = 64 * 1024 ** 3


@pytest.fixture(autouse=True)
def _mock_psutil_resources():
    """Auto-patch psutil virtual_memory and cpu_percent for all compound tests.

    The resource guardrail in CompoundExecutor blocks execution when system
    memory exceeds ~85% or CPU exceeds ~80%. On a busy machine (running background
    agents, EVO loop, etc.) real resources can exceed these thresholds, causing
    every test that calls execute_task to fail.
    Mocking at conftest level fixes this suite-wide without touching each test.
    """
    with (
        patch("psutil.virtual_memory", return_value=_MockVirtualMemory()),
        patch("psutil.cpu_percent", return_value=25.0),
    ):
        yield


@pytest_asyncio.fixture
async def mcp_client():
    """Create mock MCP client for testing."""
    return MagicMock(spec=MCPClient)
