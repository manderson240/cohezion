"""
Step 9 Red Tests: MHD Flux Engine (Magnetohydrodynamics).

Verifies:
1. Intent-to-Flux Mapping: Agent intent as Magnetic Flux (B).
2. Velocity Field Correlation: Reasoning trajectories as fluid flow (v).
3. Alfven Wave Detection: Information propagation via MHD oscillations.
4. Plasma Containment: HIHO stability as MHD equilibrium.
"""

import importlib.util
import sys
from unittest.mock import MagicMock, patch

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

from cohezion.physics.mhd_engine import MHDFluxEngine
from cohezion.universe.engine import UniverseSimulationEngine


@pytest.mark.asyncio
class TestMHDFlowBridge:
    """Verifies the fluid-dynamic representation of agentic intelligence."""

    async def test_flux_mapping(self):
        """Step 9.1: Engine must map intent vectors to Magnetic Flux (B)."""
        bridge = MHDFluxEngine()
        intent_vec = [0.8] * 12  # High intent

        # RED: calculate_magnetic_flux should return a vector B
        flux_b = bridge.calculate_magnetic_flux(intent_vec)

        assert len(flux_b) == 3  # 3D vector
        assert np.linalg.norm(flux_b) > 0

    async def test_alfven_wave_detection(self):
        """Step 9.2: Detect Alfven waves (intent propagation) in the swarm."""
        engine = UniverseSimulationEngine()

        # Two disparate journey points
        point_a = MagicMock()
        point_a.axiomatic.to_vector.return_value = [0.5] * 12
        point_b = MagicMock()
        point_b.axiomatic.to_vector.return_value = [0.6] * 12

        # Detect alfven_resonance should check for info-propagation
        is_resonant = engine.detect_alfven_resonance(point_a, point_b)
        assert bool(is_resonant) is True

    async def test_plasma_containment_status(self):
        """Step 9.3: HIHO stability must be reported as Plasma Containment."""
        engine = UniverseSimulationEngine()
        journey = await engine.start_journey(agent_name="Plasma", intent="Contain")

        # Perfect HIHO 0.5
        with patch("cohezion.universe.engine.AxiomaticState.coherence_score", return_value=0.5):
            point = await engine.evolve_trajectory(journey, action="Magnetize", phi_score=1.0)

            # RED: Check for MHD metadata
            mhd_data = point.metadata.get("mhd_equilibrium")
            assert mhd_data is not None
            assert mhd_data["containment_score"] > 0.9
            assert mhd_data["topology"] == "toroidal_vortex"
