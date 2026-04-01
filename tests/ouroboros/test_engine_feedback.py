from unittest.mock import AsyncMock

import pytest
import torch

from cohezion.universe.triune_engine import TriuneSimulationEngine
from cohezion.universe.triune_manifold import TriuneState


@pytest.fixture
def initial_state():
    return TriuneState(
        doer=torch.zeros(12),
        thinker=torch.zeros(512),
        knower=torch.zeros(2048)
    )

@pytest.mark.asyncio
async def test_engine_inject_patch_success(initial_state):
    """Test that Ouroboros can inject a patch proposal into the engine."""
    mock_surreal = AsyncMock()
    mock_obsidian = AsyncMock()
    
    engine = TriuneSimulationEngine(
        state=initial_state,
        surreal_logger=mock_surreal,
        obsidian_mcp=mock_obsidian
    )
    
    patch_proposal = "PATCH Proposal: Adjust manifold stiffness to 0.15."
    
    # This method should be implemented in the engine
    await engine.inject_patch(patch_proposal)
    
    # Verify the patch was logged to Obsidian as an 'Anchor'
    mock_obsidian.store_state_summary.assert_called_once()
    kwargs = mock_obsidian.store_state_summary.call_args[1]
    assert "patch" in kwargs["trajectory_id"]
    # Check that the nudge manifested in the thinker layer
    thinker_list = kwargs["state"].thinker.tolist()
    assert any(val == pytest.approx(0.15) for val in thinker_list)
