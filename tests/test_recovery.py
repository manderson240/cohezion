import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from cohezion.agents.base import BaseAgent
from cohezion.swarm.swarm_types import SwarmConfig


@pytest.mark.anyio
async def test_mrp_synchronization():
    """Test that the agent attempts to synchronize on startup."""
    config = SwarmConfig(mrp_sync=True)

    with patch("cohezion.agents.base.SurrealClient") as mock_db_class:
        mock_db = mock_db_class.return_value
        mock_db.query = AsyncMock(return_value=[{"timestamp": "2026-01-20T23:00:00", "state_vector": [0.1] * 12}])
        mock_db.store_node = AsyncMock()  # Pre-mock this too

        # We need a concrete subclass to test BaseAgent
        class TestAgent(BaseAgent):
            async def process(self, *args, **kwargs):
                return "test"

        agent = TestAgent(model_name="test-model", config=config)

        # Wait a bit for the async task to trigger and complete step 1
        await asyncio.sleep(0.1)

        mock_db.query.assert_called_with("SELECT * FROM mission_pulse ORDER BY timestamp DESC LIMIT 1")


@pytest.mark.anyio
async def test_mrp_pulse_loop():
    """Test that the agent periodically sends a mission pulse."""
    # Use a very short interval for test (0.0001 minutes = 0.006 seconds)
    config = SwarmConfig(mrp_sync=True, mrp_pulse_interval_minutes=0.0001)

    with patch("cohezion.agents.base.SurrealClient") as mock_db_class:
        mock_db = mock_db_class.return_value
        mock_db.query = AsyncMock(return_value=[])
        mock_db.store_node = AsyncMock()

        class TestAgent(BaseAgent):
            async def process(self, *args, **kwargs):
                return "test"

        agent = TestAgent(model_name="test-model", config=config)

        # Wait for at least one pulse loop to run
        # sleeper is interval * 60, so 0.006s. 0.2s is plenty.
        await asyncio.sleep(0.2)

        assert mock_db.store_node.call_count >= 1
