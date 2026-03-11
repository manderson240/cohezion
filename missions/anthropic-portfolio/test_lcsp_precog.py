"""
Step 8 Red Tests: LCSP "Precog" Projections.

Verifies:
1. Ghost Trajectories: Iterative future state prediction via LCSP.
2. Stability Convergence: Predictions must trend toward the HIHO 0.5 attractor.
3. Precog Confidence: Confidence scores must degrade over long-horizon projections.
"""

import importlib.util
import sys
from unittest.mock import AsyncMock, MagicMock

import numpy as np
import pytest


# --- ROBUST MOCK DEPENDENCIES ---
def mock_package(name):
    mock = MagicMock()
    spec = importlib.util.spec_from_loader(name, loader=None)
    mock.__spec__ = spec
    sys.modules[name] = mock
    return mock


mock_package("pocket_tts")
mock_package("pocket_tts.modules.stateful_module")
mock_package("soundfile")
mock_package("transformers")

from cohezion.universe.engine import UniverseSimulationEngine


@pytest.mark.asyncio
class TestLCSPPrecog:
    """Verifies the predictive 'Prevision' layer of the manifold."""

    async def test_ghost_trajectory_generation(self):
        """Step 8.1: Engine must generate iterative future projections."""
        mock_encoder = AsyncMock()
        mock_encoder.encode.return_value = [0.5] * 2048
        engine = UniverseSimulationEngine(encoder=mock_encoder)

        journey = await engine.start_journey(agent_name="Precog", intent="See the future")
        await engine.evolve_trajectory(journey, action="Observe", phi_score=0.9)

        # RED: generate_precog_projection should return 5 future steps
        projections = await engine.generate_precog_projection(journey, steps=5)

        assert len(projections) == 5
        assert "axiomatic_vector" in projections[0]
        assert len(projections[0]["axiomatic_vector"]) == 12

        async def test_stability_convergence(self):
            """Step 8.2: Future states should trend toward HIHO 0.5 stability."""
            mock_encoder = AsyncMock()
            mock_encoder.encode.return_value = [0.1] * 2048  # High instability start
            engine = UniverseSimulationEngine(encoder=mock_encoder)

            journey = await engine.start_journey(agent_name="Precog", intent="Stabilize")
            await engine.evolve_trajectory(journey, action="Perturb", phi_score=0.5)

            projections = await engine.generate_precog_projection(journey, steps=10)

            # Verify the TREND: Average stability of projections should be high (> 0.8)
            # given the initial state was very unstable (0.1)
            avg_stability = np.mean([p["stability"] for p in projections])

            # Initial instability (0.1) leads to ~0.6 stability.
            # Attractor logic should pull it way above that on average.
            assert avg_stability > 0.8

    async def test_precog_confidence_degradation(self):
        """Step 8.3: Confidence must degrade as projection horizon increases."""
        # Note: Current LCSP implementation's confidence is tied 1:1 to stability.
        # For a truly 'precog' feel, we want confidence to drop over time.
        # RED: Adjust engine logic if confidence doesn't degrade.
        engine = UniverseSimulationEngine()
        mock_journey = MagicMock()
        mock_journey.trajectory = [MagicMock()]
        mock_journey.trajectory[-1].axiomatic.to_vector.return_value = [0.5] * 12

        projections = await engine.generate_precog_projection(mock_journey, steps=5)

        # Verify: Confidence should drop over time (Temporal Entropy)
        assert projections[-1]["confidence"] < projections[0]["confidence"]
