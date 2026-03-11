"""
Acceptance Tests for the Minority Report Observatory.

This test file defines the "Red" phase for the first deliverable of the portfolio.
It verifies the integration of the UniverseSimulationEngine with the 4 Fabrics,
the HIHO 0.5 stability point, and the Multi-modal hook.
"""

import importlib.util
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# --- ROBUST MOCK DEPENDENCIES ---
def mock_package(name):
    mock = MagicMock()
    # Create a dummy spec to satisfy importlib.util.find_spec
    spec = importlib.util.spec_from_loader(name, loader=None)
    mock.__spec__ = spec
    sys.modules[name] = mock
    return mock


mock_pocket = mock_package("pocket_tts")
mock_package("pocket_tts.modules.stateful_module")
mock_sf = mock_package("soundfile")

# Also mock transformers to prevent it from trying to load soundfile
mock_package("transformers")

from cohezion.universe.engine import AxiomaticState, UniverseSimulationEngine


@pytest.mark.asyncio
class TestObservatoryInitialization:
    """Verifies the 'Awareness of Nothing' (Void) state and First Perturbation."""

    async def test_void_initialization(self):
        """Step 1.1: The simulation must start in a zero-state (The Void)."""
        # Mock the encoder to avoid real LLM/Vector calls
        mock_encoder = AsyncMock()
        mock_encoder.encode.return_value = [0.0] * 2048

        engine = UniverseSimulationEngine(encoder=mock_encoder)

        # We start a journey with 'void' intent
        journey = await engine.start_journey(agent_name="Observer", intent="Awareness of Nothing")

        # INITIAL AXIOMATIC STATE: Default params
        assert journey.initial_axiomatic.spatial_x == 0.0
        assert journey.status == "active"
        assert journey.initial_latent is not None

    async def test_first_perturbation_impact(self):
        """Step 1.2: Clicking 'Perturb the Void' must trigger a Tempic change."""
        mock_encoder = AsyncMock()
        mock_encoder.encode.return_value = [0.1] * 2048

        engine = UniverseSimulationEngine(encoder=mock_encoder)
        journey = await engine.start_journey(agent_name="Observer", intent="Perturb the Void")

        # We take a 'Perturbation' step
        point = await engine.evolve_trajectory(
            journey,
            action="Perturb the Void",
            phi_score=0.8,  # High-quality initial act
        )

        # VERIFY TEMPIC FIELD: Rate of change must be > 0
        state_before = journey.initial_axiomatic
        state_after = point.axiomatic

        tempic = AxiomaticState.compute_tempic(state_before, state_after)
        assert tempic > 0.0, "The first perturbation must precipitate change (Tempic > 0)"

        # VERIFY SPIN COHERENCE
        assert state_after.spin_coherence == 1.0

    async def test_multimodal_nexus_hook(self):
        """Step 1.3: The journey must schedule Kyutai audio and visuals."""
        # Patch the BRIDGE in its original module
        with patch(
            "cohezion.core.multimodal_bridge.LOCAL_MULTIMODAL_BRIDGE.schedule_asset", new_callable=AsyncMock
        ) as mock_schedule:
            mock_encoder = AsyncMock()
            mock_encoder.encode.return_value = [0.0] * 2048
            engine = UniverseSimulationEngine(encoder=mock_encoder)

            # This should trigger narrative and storyboard assets
            await engine.start_journey(agent_name="Observer", intent="Initialize Precipitation")

            # Check if assets were scheduled
            assert mock_schedule.call_count >= 2

            # First call should be the narrative (Kyutai voice)
            call_args = mock_schedule.call_args_list[0]
            args, kwargs = call_args
            assert args[0] == "narrative"

            # Extract payload from args or kwargs
            payload = kwargs.get("payload") or args[2]
            assert "Initializing manifold journey" in payload["text"]

    async def test_surrealdb_persistence(self):
        """Step 1.4: Journey physics states must be stored in SurrealDB."""
        # Mock SurrealDB client
        mock_db = AsyncMock()
        mock_encoder = AsyncMock()
        mock_encoder.encode.return_value = [0.0] * 2048

        engine = UniverseSimulationEngine(encoder=mock_encoder, db_client=mock_db)

        journey = await engine.start_journey(agent_name="Observer", intent="Test Persistence")

        # Verify db_client.create was called with 'universe_journey'
        assert mock_db.create.called
        call_args = mock_db.create.call_args
        assert call_args[0][0] == "universe_journey"
        assert call_args[0][1]["id"] == journey.id
