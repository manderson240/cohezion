from unittest.mock import AsyncMock

import pytest
import torch

from cohezion.universe.triune_engine import TriuneSimulationEngine
from cohezion.universe.triune_manifold import TriuneState


@pytest.fixture
def initial_state():
    return TriuneState(doer=torch.zeros(12), thinker=torch.zeros(512), knower=torch.zeros(2048))


@pytest.mark.asyncio
async def test_engine_initialization(initial_state):
    """Test that the engine initializes with state and loggers."""
    mock_surreal = AsyncMock()
    mock_obsidian = AsyncMock()

    engine = TriuneSimulationEngine(state=initial_state, surreal_logger=mock_surreal, obsidian_mcp=mock_obsidian)

    assert engine.state == initial_state
    assert engine.surreal_logger == mock_surreal
    assert engine.obsidian_mcp == mock_obsidian


@pytest.mark.asyncio
async def test_engine_step_persistence(initial_state):
    """Test that a simulation step triggers persistence calls."""
    mock_surreal = AsyncMock()
    mock_obsidian = AsyncMock()

    engine = TriuneSimulationEngine(state=initial_state, surreal_logger=mock_surreal, obsidian_mcp=mock_obsidian)

    # We provide a dummy 'environment' for coherence calculation
    dummy_env = torch.ones(12)

    await engine.step(dt=0.1, environment=dummy_env, trajectory_id="step_test_1")

    # Verify loggers were called
    mock_surreal.log_trajectory.assert_called_once()
    mock_obsidian.store_state_summary.assert_called_once()

    # Verify state was updated (e.g. doer should have changed if we implement simple drift)
    # For now, we just check that coherence was passed
    args, _ = mock_surreal.log_trajectory.call_args
    assert args[0] == "step_test_1"
    assert isinstance(args[2], float)  # coherence


@pytest.mark.asyncio
async def test_engine_step_persistence_failure(initial_state):
    """Test handling of persistence failure during step."""
    mock_surreal = AsyncMock()
    mock_surreal.log_trajectory.side_effect = Exception("Surreal Failure")
    mock_obsidian = AsyncMock()

    engine = TriuneSimulationEngine(state=initial_state, surreal_logger=mock_surreal, obsidian_mcp=mock_obsidian)

    with pytest.raises(Exception, match="Surreal Failure"):
        await engine.step(dt=0.1, environment=torch.ones(12), trajectory_id="fail_test")
