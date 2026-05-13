from pathlib import Path
from unittest.mock import patch

import pytest

from cohezion.mass_sim.config import ScaleTier, SimulationConfig
from cohezion.mass_sim.orchestrator import MassSimOrchestrator


@pytest.mark.asyncio
@pytest.mark.integration
async def test_demo_scale_integration(tmp_path: Path):
    tier = ScaleTier("test_demo", n_agents=10, n_epochs=5, n_universes=2, checkpoint_interval=5, batch_size=10)
    config = SimulationConfig(
        scale=tier,
        use_navigator=False,
        persist_to_db=False,
        artifact_dir=tmp_path / "artifacts",
        checkpoint_dir=tmp_path / "checkpoints",
        universe_seeds=[42, 43],
    )

    orchestrator = MassSimOrchestrator(config)
    # Mock memory guard to prevent swap-based abort (this machine has >20GB swap used)
    with patch.object(orchestrator.guard, "should_abort", return_value=False):
        report = await orchestrator.run()

    assert report.n_universes == 2
    assert report.n_agents == 10
    assert report.n_epochs == 5
    assert len(report.universe_results) == 2

    # Check results populated correctly
    ur = report.universe_results[0]
    assert "pct_elements_within_bounds" in ur.final_stats
    assert "pct_agents_majority_in_bounds" in ur.final_stats
