"""TDD Framework for EcoResilience Stability Invariants.
Validates that the manifold projection maintains critical coherence
during la-phase transitions.
"""

from __future__ import annotations

import numpy as np
import pytest

from cohezion.compound.stability_guard import HIHOStabilityGuard
from cohezion.flume.manifolds.translator import ManifoldProjection, ManifoldTranslator
from cohezion.flume.vae_encoder import FlumeVAEEncoder


# INVARIANT: Manifold coherence must never drop below 0.4 for a stable state.
STABILITY_THRESHOLD = 0.4


@pytest.fixture
def mock_translator():
    encoder = FlumeVAEEncoder()
    return ManifoldTranslator(encoder=encoder)


@pytest.fixture
def stability_guard():
    return HIHOStabilityGuard(threshold=STABILITY_THRESHOLD)


@pytest.mark.asyncio
async def test_stability_invariant_low_coherence():
    """Test that the guard correctly flags instability when coherence < 0.4."""
    guard = HIHOStabilityGuard(threshold=STABILITY_THRESHOLD)
    projection = ManifoldProjection(
        coordinates=np.random.randn(12),
        coherence=0.2,  # Fails invariant
        stability=False,
    )
    result = await guard.verify(projection, "Some strategy")
    assert result.is_stable is False
    assert result.coherence == 0.2


@pytest.mark.asyncio
async def test_stability_invariant_high_coherence():
    """Test that the guard correctly flags stability when coherence >= 0.4."""
    guard = HIHOStabilityGuard(threshold=STABILITY_THRESHOLD)
    projection = ManifoldProjection(
        coordinates=np.random.randn(12),
        coherence=0.7,  # Passes invariant
        stability=True,
    )
    result = await guard.verify(projection, "Some strategy")
    assert result.is_stable is True
    assert result.coherence == 0.7


def test_manifold_projection_consistency():
    """
    TDD: Ensure the ManifoldTranslator maintains consistent
    projections for identical textual inputs.
    """
    translator = ManifoldTranslator(encoder=FlumeVAEEncoder())
    text = "Sabu-Sabu la-phase indigenous planting sequence."

    proj1 = translator.project(translator.encoder.encode(text))
    proj2 = translator.project(translator.encoder.encode(text))

    np.testing.assert_array_almost_equal(proj1.coordinates, proj2.coordinates)
    assert proj1.coherence == proj2.coherence


if __name__ == "__main__":
    # Manual run for validation
    import pytest

    pytest.main([__file__])
