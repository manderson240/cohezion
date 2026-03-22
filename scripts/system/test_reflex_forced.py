import asyncio
import logging
import sys
from unittest.mock import MagicMock


# Mock vitals before importing reflex
sys.modules["cohezion.reliability.monitor"] = MagicMock()
sys.modules["cohezion.reliability.monitor"].get_resource_monitor.return_value.get_vitals.return_value = {
    "cpu_percent": 10.0,
    "memory_percent": 30.0,
    "vram_percent": 20.0,
}

from cohezion.evolution.reflex import ReflexAgent


async def test_reflex():
    agent = ReflexAgent()
    # Mock safe_to_run just in case
    agent._safe_to_run = MagicMock(return_value=asyncio.Future())
    agent._safe_to_run.return_value.set_result(True)

    print("🚀 forcing reflex run...")
    await agent.scan_and_reflect()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(test_reflex())
