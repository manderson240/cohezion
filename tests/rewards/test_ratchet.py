from unittest.mock import AsyncMock

import pytest
import torch

from cohezion.rewards.ratchet import RatchetMechanism
from cohezion.universe.triune_manifold import TriuneState


@pytest.fixture
def triune_state():
    return TriuneState(
        doer=torch.randn(12),
        thinker=torch.randn(512),
        knower=torch.randn(2048)
    )

@pytest.mark.asyncio
async def test_ratchet_triggers_on_high_score(triune_state):
    """Test that ratchet persists state when score exceeds threshold."""
    mock_obsidian = AsyncMock()
    ratchet = RatchetMechanism(obsidian_mcp=mock_obsidian, threshold=0.9)
    
    await ratchet.evaluate_and_ratchet(
        trajectory_id="top_tier_journey",
        state=triune_state,
        score=0.95,
        coherence=0.5
    )
    
    # Verify persistence was triggered
    mock_obsidian.store_state_summary.assert_called_once()
    args, kwargs = mock_obsidian.store_state_summary.call_args
    assert "top_tier_journey" in kwargs["trajectory_id"]
    assert "ratchet" in kwargs["trajectory_id"]

@pytest.mark.asyncio
async def test_ratchet_ignores_low_score(triune_state):
    """Test that ratchet does not persist state when score is below threshold."""
    mock_obsidian = AsyncMock()
    ratchet = RatchetMechanism(obsidian_mcp=mock_obsidian, threshold=0.9)
    
    await ratchet.evaluate_and_ratchet(
        trajectory_id="mid_tier_journey",
        state=triune_state,
        score=0.5,
        coherence=0.3
    )
    
    # Verify persistence was NOT triggered
    mock_obsidian.store_state_summary.assert_not_called()
