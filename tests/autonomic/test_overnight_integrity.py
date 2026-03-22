import pytest
import asyncio
from pathlib import Path
from scripts.overnight_autonomous_run import OvernightMission
from scripts.jobs.elegance_engine import manifest_elegance
from cohezion.core.persistence.surreal_client import SurrealClient

def test_autonomic_scripts_loadable():
    """Verify that autonomous scripts are grounded in real components."""
    # If this fails, the scripts are still hallucinating imports
    assert OvernightMission is not None
    assert manifest_elegance is not None

def test_trackio_vitals():
    """Verify trackio setup in elegance engine is breathable (No invalid args)."""
    content = Path("scripts/jobs/elegance_engine.py").read_text()
    assert "run_name=" not in content, "Found invalid 'run_name' in trackio.init"

@pytest.mark.asyncio
async def test_surreal_substrate_alive():
    """Verify SurrealDB 3.0 connection is stable."""
    client = SurrealClient(url="ws://localhost:8000/rpc", namespace="cohezion", database="logs")
    assert await client.is_alive(), "SurrealDB substrate is offline"
