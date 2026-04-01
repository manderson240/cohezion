"""Tests for substrate/overload_coordinator.py.

Covers graduated overload protection and memory pressure handling.
"""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import pytest

from cohezion.substrate.overload_coordinator import (
    OverloadCoordinator,
    OverloadError,
    ProtectionConfig,
    ProtectionLevel,
)


@pytest.fixture
def coordinator():
    # Use short intervals for testing
    config = ProtectionConfig(
        min_action_interval=0.1,
        cooldown_period=0.1
    )
    return OverloadCoordinator(config=config)

@pytest.mark.asyncio
async def test_handle_memory_pressure_graduated(coordinator):
    """[P0] Should escalate protection levels based on pressure."""
    with patch("httpx.AsyncClient.get") as mock_get, \
         patch("httpx.AsyncClient.post") as mock_post:
        
        mock_get.return_value = MagicMock(status_code=200)
        mock_get.return_value.json.return_value = {"models": [{"name": "m1"}]}
        mock_post.return_value = MagicMock(status_code=200)

        # 1. Normal (0.5)
        action = await coordinator.handle_memory_pressure(0.5)
        assert action.level == ProtectionLevel.NORMAL
        
        # 2. Warning (0.7)
        time.sleep(0.15) # Wait for cooldown
        action = await coordinator.handle_memory_pressure(0.7)
        assert action.level == ProtectionLevel.WARNING
        assert action.context_reduction_percent == 25
        
        # 3. Elevated (0.8)
        time.sleep(0.15)
        action = await coordinator.handle_memory_pressure(0.8)
        assert action.level == ProtectionLevel.ELEVATED
        assert action.context_reduction_percent == 50

@pytest.mark.asyncio
async def test_validate_request_reduction(coordinator):
    """[P0] Should reduce context window in request."""
    # Force WARNING level
    with patch("httpx.AsyncClient.get"), patch("httpx.AsyncClient.post"):
        await coordinator.handle_memory_pressure(0.7)
    
    request = {"options": {"num_ctx": 4096}}
    validated = await coordinator.validate_request(request)
    
    # 25% reduction: 4096 * 0.75 = 3072
    assert validated["options"]["num_ctx"] == 3072

@pytest.mark.asyncio
async def test_emergency_mode_rejection(coordinator):
    """[P0] Should reject requests in emergency mode."""
    with patch("httpx.AsyncClient.get"), patch("httpx.AsyncClient.post"):
        # 0.93 is EMERGENCY level
        await coordinator.handle_memory_pressure(0.93)
    
    with pytest.raises(OverloadError) as exc:
        await coordinator.validate_request({"test": True})
    assert "emergency mode" in str(exc.value)

@pytest.mark.asyncio
async def test_cooldown_active(coordinator):
    """[P0] Should respect min_action_interval."""
    with patch("httpx.AsyncClient.get"), patch("httpx.AsyncClient.post"):
        # First action
        await coordinator.handle_memory_pressure(0.7)
        # Immediate second action should be throttled
        action = await coordinator.handle_memory_pressure(0.8)
        assert "cooldown_active" in action.actions
        assert coordinator.get_status()["current_level"] == "warning"
