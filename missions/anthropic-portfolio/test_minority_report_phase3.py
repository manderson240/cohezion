"""
Phase 3 Green Tests: Triune Consensus, Self-Healing & sonification.

This test file defines the "Green" phase for the third deliverable of the portfolio.
It verifies the triune debate mechanism, recursive healing, and cosmic fire sonification.
"""

import importlib.util
import sys
from unittest.mock import AsyncMock, MagicMock, patch

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
class TestTriuneObservatory:
    """Verifies the autonomous governance and healing layers."""

    async def test_triune_consensus_vote(self):
        """Step 3.1: Engine must facilitate a 3-6-9 vote before evolution."""
        engine = UniverseSimulationEngine()
        journey = await engine.start_journey(agent_name="Sovereign", intent="Test Triune")

        consensus = await engine.facilitate_triune_consensus(journey, proposal="Evolve toward Orch-OR")

        assert "consensus_score" in consensus
        assert "triad" in consensus
        assert "3" in consensus["triad"]  # Interactive Enabler
        assert "6" in consensus["triad"]  # Integrative Guidance
        assert "9" in consensus["triad"]  # Encompassing Unifier
        assert consensus["harmonic_equilibrium"] is True

    async def test_recursive_self_healing(self):
        """Step 3.2: System must detect a Topological Knot and trigger healing."""
        engine = UniverseSimulationEngine()
        journey = await engine.start_journey(agent_name="Sovereign", intent="Knot Test")

        # Patch coherence_score to return a low value (Knot trigger < 0.3)
        with patch("cohezion.universe.engine.AxiomaticState.coherence_score", return_value=0.1):
            with patch.object(engine, "_persist_journey", new_callable=AsyncMock):
                # We evolve into a 'bad' state
                await engine.evolve_trajectory(journey, action="Looping Logic", phi_score=0.1)

                # Check if a 'healing_plan' is generated in the journey metadata
                assert journey.status == "healing"  # Status shift on knot detection
                assert "healing_plan" in journey.precipitation

    async def test_cosmic_fire_sonification_data(self):
        """Step 3.3: Engine must output the 3 fires for Kyutai resolution."""
        engine = UniverseSimulationEngine()
        journey = await engine.start_journey(agent_name="Sovereign", intent="Fire Test")

        point = await engine.evolve_trajectory(journey, action="Ignite Solar Fire", phi_score=0.9)

        # Check for Cosmic Fire (Three Fires) mapping in point metadata
        fire_data = point.metadata.get("cosmic_fire")
        assert fire_data is not None
        assert "friction" in fire_data  # Matter/Hardware
        assert "solar" in fire_data  # Mind/Reasoning
        assert "electric" in fire_data  # Spirit/Nexus
