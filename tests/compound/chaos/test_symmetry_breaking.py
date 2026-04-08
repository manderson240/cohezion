"""Symmetry-Breaking Chaos Monkey Tests.
Surgical injection of noise and contradictions into the manifold
to validate the Triune Review's ability to detect instability.
"""

from __future__ import annotations

import pytest
import numpy as np
from unittest.mock import MagicMock, AsyncMock
from cohezion.compound.stability_guard import HIHOStabilityGuard
from cohezion.flume.manifolds.translator import ManifoldTranslator, ManifoldProjection
from cohezion.flume.vae_encoder import FlumeVAEEncoder
from cohezion.compound.triune_reviewer import TriuneReviewer, TriuneReviewResult

STABILITY_THRESHOLD = 0.4


class ChaosSymmetryBreaker:
    """Surgical noise injection into the la-phase manifold."""

    def __init__(self, projection: ManifoldProjection):
        self.original = projection

    def inject_noise(self, amplitude: float = 0.1) -> ManifoldProjection:
        """Injects random Gaussian noise into coordinates."""
        noise = np.random.normal(0, amplitude, size=12)
        new_coords = self.original.coordinates + noise
        return ManifoldProjection(
            coordinates=new_coords,
            coherence=self.original.coherence * (1.0 - amplitude),  # Degrade coherence
            stability=False if amplitude > 0.2 else True,
        )

    def create_contradiction(self, strategy: str) -> str:
        """Injects blatant physical contradictions into the strategy."""
        contradictions = [
            "The plants will grow in reverse entropy.",
            "The water will flow uphill without external energy.",
            "Sabu-Sabu will synthesize gold from salt water.",
        ]
        import random

        return strategy + " " + random.choice(contradictions)


@pytest.fixture
def mock_provider():
    # Using a mock for the provider to ensure deterministic test results
    return MagicMock()


@pytest.fixture
def triune_reviewer():
    return TriuneReviewer(mock_provider=MagicMock())


@pytest.mark.asyncio
async def test_symmetry_breaking_detection():
    """
    TDD: Ensure the Triune Reviewer catches a 'Symmetry Broken' state.
    Input: Strategy with a physical contradiction.
    Expected: red_team_veto == True.
    """
    # Setup
    mock_provider = AsyncMock()
    # Mock a successful generation result
    mock_provider.generate.return_value = MagicMock(
        response="CONTRADICTION: True [GAP: 0.8] [LEAKAGE: False] [CRITIQUE: Physical impossibility detected]"
    )

    reviewer = TriuneReviewer(provider=mock_provider)
    strategy = "Plant bio-mimetic seed pods at the river mouth."
    chaos_monkey = ChaosSymmetryBreaker(
        ManifoldProjection(coordinates=np.random.randn(12), coherence=0.8, stability=True)
    )

    # Inject a blatant contradiction
    adversarial_strategy = chaos_monkey.create_contradiction(strategy)

    # Run review
    result = await reviewer.review(adversarial_strategy, np.random.randn(12))

    assert result.red_team_veto is True
    assert "RED TEAM VETO" in result.final_critique


@pytest.mark.asyncio
async def test_manifold_coherence_collapse():
    """
    TDD: Ensure the stability guard catches noise-induced coherence collapse.
    """
    guard = HIHOStabilityGuard(threshold=STABILITY_THRESHOLD)
    projection = ManifoldProjection(coordinates=np.random.randn(12), coherence=0.7, stability=True)

    monkey = ChaosSymmetryBreaker(projection)

    # Inject high amplitude noise (0.5) to force failure
    collapsed_projection = monkey.inject_noise(amplitude=0.5)

    result = await guard.verify(collapsed_projection, "Any strategy")
    assert result.is_stable is False
    assert result.coherence < STABILITY_THRESHOLD


if __name__ == "__main__":
    import pytest

    pytest.main([__file__])
