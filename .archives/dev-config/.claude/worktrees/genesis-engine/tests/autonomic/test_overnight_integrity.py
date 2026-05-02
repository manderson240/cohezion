from pathlib import Path

import pytest

from cohezion.core.persistence.surreal_client import SurrealClient
from cohezion.simulation.enhanced_simulator import EnhancedSimulator
from scripts.jobs.elegance_engine import manifest_elegance
from scripts.overnight_autonomous_run import OvernightMission


def test_autonomic_scripts_loadable():
    """Verify that autonomous scripts are grounded in real components."""
    # If this fails, the scripts are still hallucinating imports
    assert OvernightMission is not None
    assert manifest_elegance is not None
    assert EnhancedSimulator is not None


@pytest.mark.asyncio
async def test_enhanced_simulator_functional():
    """Verify that EnhancedSimulator can run a basic batch."""
    simulator = EnhancedSimulator()
    results = await simulator.run_batch(2)
    assert len(results) == 2
    assert simulator.total_completed >= 2


def test_trackio_vitals():
    """Verify trackio setup in elegance engine is breathable (No invalid args)."""
    content = Path("scripts/jobs/elegance_engine.py").read_text()
    assert "run_name=" not in content, "Found invalid 'run_name' in trackio.init"


@pytest.mark.asyncio
async def test_surreal_substrate_alive():
    """Verify SurrealDB 3.0 connection is stable."""
    client = SurrealClient(url="ws://localhost:8000/rpc", namespace="cohezion", database="logs")
    assert await client.is_alive(), "SurrealDB substrate is offline"
