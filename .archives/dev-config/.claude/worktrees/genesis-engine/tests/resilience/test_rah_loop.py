"""Integration test for RAH Autonomic Loop."""

import asyncio
from unittest.mock import MagicMock

import pytest

from cohezion.resilience.manager import AutonomicManager


@pytest.mark.asyncio
async def test_rah_analysis_logic():
    """Verify that the analysis logic correctly selects strategies based on vitals."""
    manager = AutonomicManager()

    # Test Emergency
    vitals_emergency = {"cpu_percent": 99, "memory_percent": 50}
    analysis = manager._analyze_vitals(vitals_emergency)
    assert analysis["action_needed"] is True
    assert analysis["strategy"] == "system_restart"

    # Test High Pressure (RAM)
    vitals_high_ram = {"cpu_percent": 50, "memory_percent": 92}
    analysis = manager._analyze_vitals(vitals_high_ram)
    assert analysis["action_needed"] is True
    assert analysis["strategy"] == "context_reduction"

    # Test Normal
    vitals_normal = {"cpu_percent": 20, "memory_percent": 30}
    analysis = manager._analyze_vitals(vitals_normal)
    assert analysis["action_needed"] is False


@pytest.mark.asyncio
async def test_rah_execution_flow():
    """Verify that the manager correctly triggers a strategy execution."""
    manager = AutonomicManager()

    # Mock strategy
    mock_strategy = MagicMock()
    mock_strategy.execute = MagicMock(return_value=asyncio.Future())
    mock_strategy.execute.return_value.set_result(True)

    manager._strategies["test_strat"] = mock_strategy

    analysis = {"action_needed": True, "strategy": "test_strat", "context": {"test": "data"}}

    vitals = {"cpu_percent": 85, "memory_percent": 50}
    await manager._execute_healing(analysis, vitals)

    mock_strategy.execute.assert_called_once_with({"test": "data"})
