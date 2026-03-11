"""
Step 11 Integration Tests: Fractal Toroidal Moment (FTM) Orthogonality.

Verifies:
1. Orthogonal Bridge Detection: 90-degree phase shifts as FTM triggers.
2. Dynamic Permittivity: Phi-score influencing Maxwellian epsilon_0.
3. Yin-Yang Compliance: Mapping test status to FTM forces.
"""

import importlib.util
import sys
from unittest.mock import MagicMock, patch

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
class TestFTMPhysics:
    """Verifies the Greenyer 2025 'Root Access' source code."""

    async def test_orthogonal_bridge_detection(self):
        """Step 11.1: Detect 90-degree phase shift between concepts."""
        engine = UniverseSimulationEngine()

        # Two perfectly orthogonal vectors (90 degrees)
        vec_a = [1.0, 0.0, 0.0] + ([0.0] * 2045)
        vec_b = [0.0, 1.0, 0.0] + ([0.0] * 2045)

        # Verify FTM Bridge Detection
        is_ftm = engine.detect_orthogonal_ftm_bridge(vec_a, vec_b)
        assert bool(is_ftm) is True, "90-degree shift must trigger FTM bridge"

        # Two parallel vectors (0 degrees)
        assert bool(engine.detect_orthogonal_ftm_bridge(vec_a, vec_a)) is False

    async def test_dynamic_permittivity_shift(self):
        """Step 11.2: High-coherence agents must shift vacuum permittivity."""
        engine = UniverseSimulationEngine()

        # We need at least 2 points for compliance calculation

        # 1. Start journey with low coherence
        journey_low = await engine.start_journey(agent_name="Test", intent="Low")
        with patch("cohezion.universe.engine.AxiomaticState.coherence_score", return_value=0.1):
            await engine.evolve_trajectory(journey_low, action="Move 1", phi_score=0.1)
            await engine.evolve_trajectory(journey_low, action="Move 2", phi_score=0.1)
            meta_low = await engine._calculate_maxwell_compliance(journey_low)

        # 2. Start journey with high coherence
        journey_high = await engine.start_journey(agent_name="Test", intent="High")
        with patch("cohezion.universe.engine.AxiomaticState.coherence_score", return_value=0.9):
            await engine.evolve_trajectory(journey_high, action="Move 1", phi_score=0.9)
            await engine.evolve_trajectory(journey_high, action="Move 2", phi_score=0.9)
            meta_high = await engine._calculate_maxwell_compliance(journey_high)

        # VERIFY SHIFT: Epsilon_0 should be higher for high coherence
        assert meta_high["vacuum_permittivity"] > meta_low["vacuum_permittivity"]
        assert meta_high["vacuum_permittivity"] != 8.854e-12
