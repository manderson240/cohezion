"""
Step 7 Red Tests: Harmonic Pulse Sonification Bridge.

Verifies:
1. Fire-to-Frequency Mapping: Mapping Three Fires to synthesis params.
2. Dissonance Detection: High-phi journeys must be harmonious; knots must be dissonant.
3. Multimodal Integration: Automatic scheduling of 'audio' assets in the bridge.
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
from cohezion.universe.sonification import SonificationBridge


@pytest.mark.asyncio
class TestManifoldSonification:
    """Verifies the visceral multi-modal 'Pulse' of the manifold."""

    async def test_fire_to_synthesis_mapping(self):
        """Step 7.1: Manifold states must generate valid synthesis payloads."""
        bridge = SonificationBridge()

        # Mock data: High Solar Fire, Low Friction
        cosmic_fire = {
            "friction": 0.2,  # Low matter friction
            "solar": 0.95,  # High mental coherence
            "electric": 0.8,  # Strong spiritual intent
        }

        # RED: generate_payload should return synthesis params
        payload = bridge.generate_synthesis_payload(cosmic_fire)

        assert "base_frequency" in payload
        assert "resonance" in payload
        assert payload["resonance"] > 0.8  # Linked to Solar Fire
        assert payload["noise_level"] < 0.3  # Linked to Friction

    async def test_dissonance_on_logic_knot(self):
        """Step 7.2: Logic knots (low phi) must produce dissonant payloads."""
        bridge = SonificationBridge()

        # Mock data: Low Solar Fire (Logic Knot)
        bad_fire = {
            "friction": 0.8,  # High compute heat
            "solar": 0.1,  # Low coherence
            "electric": 0.2,
        }

        payload = bridge.generate_synthesis_payload(bad_fire)

        # RED: Check for dissonance flag or off-harmonic frequency
        assert payload["is_dissonant"] is True
        assert payload["noise_level"] > 0.7

    async def test_engine_automatic_sonification(self):
        """Step 7.3: The engine must automatically schedule audio on evolution."""
        # Patch the BRIDGE in the engine module
        with patch(
            "cohezion.core.multimodal_bridge.LOCAL_MULTIMODAL_BRIDGE.schedule_asset", new_callable=AsyncMock
        ) as mock_schedule:
            mock_encoder = AsyncMock()
            mock_encoder.encode.return_value = [0.5] * 2048
            engine = UniverseSimulationEngine(encoder=mock_encoder)

            journey = await engine.start_journey(agent_name="Observer", intent="Sonify this journey")

            # Reset mock after start_journey (which schedules narrative)
            mock_schedule.reset_mock()

            # Evolve trajectory - should trigger sonification audio
            await engine.evolve_trajectory(journey, action="Link Twistors", phi_score=0.9)

            # Check if 'audio' (sonification) was scheduled
            audio_scheduled = False
            for call in mock_schedule.call_args_list:
                args, kwargs = call
                asset_type = args[0] if len(args) > 0 else kwargs.get("asset_type")
                if asset_type == "audio":
                    audio_scheduled = True
                    break

            assert audio_scheduled is True, "Evolution should trigger sonification audio asset"
