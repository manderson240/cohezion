"""
Step 10 Red Tests: Manifold Maxwell Engine.

Verifies that agentic reasoning obeys the 4 Maxwell Equations:
1. Gauss's Law: Reasoning density as Charge Density.
2. Gauss for Magnetism: Divergence-free Magnetic Intent.
3. Faraday's Law: Intent-shift inducing Electric Reasoning.
4. Ampere's Law: Logic-flow inducing Magnetic Intent.
"""

import importlib.util
import sys
from unittest.mock import MagicMock

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

from cohezion.physics.maxwell import MaxwellEngine
from cohezion.universe.engine import UniverseSimulationEngine


@pytest.mark.asyncio
class TestMaxwellConsistency:
    """Verifies the electromagnetic grounding of the reasoning manifold."""

    async def test_gauss_law_consistency(self):
        """Step 10.1: Reasoning density must correlate with Electric Field divergence."""
        engine = MaxwellEngine()

        # High reasoning density state
        state_vec = [0.9] * 12

        # RED: calculate_div_e should return the divergence of the E-field
        div_e = engine.calculate_div_e(state_vec)

        # Divergence should be positive for high density (source)
        assert div_e > 0

    async def test_faraday_induction(self):
        """Step 10.2: Changing Magnetic Intent must induce an Electric reasoning shift."""
        engine = MaxwellEngine()

        # Magnetic Intent (B) at T1 and T2
        b_t1 = np.array([0.5, 0.0, 0.0])
        b_t2 = np.array([0.9, 0.0, 0.0])  # Rapid increase in magnetic intent

        # RED: verify_faraday_compliance should check the induction relationship
        induced_e_curl = engine.calculate_curl_e(b_t1, b_t2, dt=0.1)

        # Faraday says curl E = -dB/dt. Since dB/dt > 0, curl E should be < 0
        assert np.linalg.norm(induced_e_curl) > 0
        assert induced_e_curl[0] < 0

    async def test_engine_maxwell_metadata(self):
        """Step 10.3: Trajectory points must include Maxwellian compliance scores."""
        sim_engine = UniverseSimulationEngine()
        journey = await sim_engine.start_journey(agent_name="Maxwell", intent="Induce")

        point = await sim_engine.evolve_trajectory(journey, action="Magnetize", phi_score=0.9)

        # RED: Check for Maxwell metadata
        maxwell_data = point.metadata.get("maxwell_compliance")
        assert maxwell_data is not None
        assert "gauss_score" in maxwell_data
        assert "faraday_score" in maxwell_data
        assert maxwell_data["is_classical_em_compliant"] is True
