from unittest.mock import MagicMock

import pytest

from cohezion.evolution.reflex import ReflexAgent


@pytest.fixture
def reflex_agent():
    agent = ReflexAgent()
    agent.dba = MagicMock()
    agent.monitor = MagicMock()
    return agent


@pytest.mark.asyncio
async def test_scan_and_reflect_happy_path(reflex_agent):
    reflex_agent.monitor.get_vitals.return_value = {
        "cpu_percent": 70,
        "memory_percent": 60,
    }
    reflex_agent._check_rate_limit.return_value = True
    reflex_agent.dba.client.query.return_value = [
        {"result": [{"dilation_factor": 0.4}]}
    ]

    await reflex_agent.scan_and_reflect()

    reflex_agent.monitor.get_vitals.assert_called_once()
    reflex_agent._check_rate_limit.assert_called_once()
    reflex_agent.dba.connect.assert_awaited_once()
    reflex_agent.dba.client.query.assert_awaited_once()


@pytest.mark.asyncio
async def test_scan_and_reflect_cpu_high(reflex_agent):
    reflex_agent.monitor.get_vitals.return_value = {
        "cpu_percent": 90,
        "memory_percent": 60,
    }

    await reflex_agent.scan_and_reflect()

    reflex_agent.monitor.get_vitals.assert_called_once()
    reflex_agent._check_rate_limit.assert_not_called()


@pytest.mark.asyncio
async def test_scan_and_reflect_memory_high(reflex_agent):
    reflex_agent.monitor.get_vitals.return_value = {
        "cpu_percent": 70,
        "memory_percent": 85,
    }

    await reflex_agent.scan_and_reflect()

    reflex_agent.monitor.get_vitals.assert_called_once()
    reflex_agent._check_rate_limit.assert_not_called()


@pytest.mark.asyncio
async def test_scan_and_reflect_vram_high(reflex_agent):
    reflex_agent.monitor.get_vitals.return_value = {
        "cpu_percent": 70,
        "memory_percent": 60,
        "vram_percent": 86,
    }

    await reflex_agent.scan_and_reflect()

    reflex_agent.monitor.get_vitals.assert_called_once()
    reflex_agent._check_rate_limit.assert_not_called()


@pytest.mark.asyncio
async def test_scan_and_reflect_rate_limit(reflex_agent):
    reflex_agent.monitor.get_vitals.return_value = {
        "cpu_percent": 70,
        "memory_percent": 60,
    }
    reflex_agent._check_rate_limit.return_value = False

    await reflex_agent.scan_and_reflect()

    reflex_agent.monitor.get_vitals.assert_called_once()
    reflex_agent._check_rate_limit.assert_called_once()


@pytest.mark.asyncio
async def test_scan_and_reflect_no_stress_events(reflex_agent):
    reflex_agent.monitor.get_vitals.return_value = {
        "cpu_percent": 70,
        "memory_percent": 60,
    }
    reflex_agent._check_rate_limit.return_value = True
    reflex_agent.dba.client.query.return_value = [{"result": []}]

    await reflex_agent.scan_and_reflect()

    reflex_agent.monitor.get_vitals.assert_called_once()
    reflex_agent._check_rate_limit.assert_called_once()
    reflex_agent.dba.connect.assert_awaited_once()
    reflex_agent.dba.client.query.assert_awaited_once()


@pytest.mark.asyncio
async def test_scan_and_reflect_insight_exists(reflex_agent):
    reflex_agent.monitor.get_vitals.return_value = {
        "cpu_percent": 70,
        "memory_percent": 60,
    }
    reflex_agent._check_rate_limit.return_value = True
    reflex_agent.dba.client.query.return_value = [
        {"result": [{"dilation_factor": 0.4}]}
    ]
    reflex_agent.insights_dir.glob.return_value = [MagicMock()]

    await reflex_agent.scan_and_reflect()

    reflex_agent.monitor.get_vitals.assert_called_once()
    reflex_agent._check_rate_limit.assert_called_once()
    reflex_agent.dba.connect.assert_awaited_once()
    reflex_agent.dba.client.query.assert_awaited_once()


@pytest.mark.asyncio
async def test_scan_and_reflect_generate_insight(reflex_agent):
    reflex_agent.monitor.get_vitals.return_value = {
        "cpu_percent": 70,
        "memory_percent": 60,
    }
    reflex_agent._check_rate_limit.return_value = True
    reflex_agent.dba.client.query.return_value = [
        {"result": [{"dilation_factor": 0.4}]}
    ]
    reflex_agent.insights_dir.glob.return_value = []

    await reflex_agent.scan_and_reflect()

    reflex_agent.monitor.get_vitals.assert_called_once()
    reflex_agent._check_rate_limit.assert_called_once()
    reflex_agent.dba.connect.assert_awaited_once()
    reflex_agent.dba.client.query.assert_awaited_once()
