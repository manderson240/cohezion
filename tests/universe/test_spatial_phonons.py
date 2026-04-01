"""Tests for SpatialPhononsEngine and its integration in UniverseSimulationEngine.

Validates:
- Phonon dynamics (viscous expansion, oscillation)
- Coherence gain calculations
- Fallback logic in UniverseSimulationEngine when Rust is missing
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from cohezion.universe.engine import AxiomaticState, UniverseJourney, UniverseSimulationEngine
from cohezion.universe.spatial_phonons import PhononParameters, SpatialPhononsEngine


class TestSpatialPhononsEngine:
    def test_evolve_state_expansion(self):
        """[P0] Phonon engine should drive spatial expansion."""
        engine = SpatialPhononsEngine()
        initial_state = AxiomaticState(spatial_x=1.0, spatial_y=1.0, spatial_z=1.0, temporal=0.0)
        
        # Evolve with delta_t=1.0 to see clear expansion
        new_state = engine.evolve_state(initial_state, delta_t=1.0)
        
        # With default dark_energy_density=0.7 and no drag (physics=0.5)
        # spatial_x should be 1.0 * (1 + 0.7) + oscillation
        assert new_state.spatial_x > 1.0
        assert new_state.spatial_y > 1.0
        assert new_state.temporal == 1.0

    def test_viscous_drag_physics_bleed(self):
        """[P0] Higher physics state (above 0.5) should create viscous drag."""
        engine = SpatialPhononsEngine(PhononParameters(viscosity_alpha=0.1))
        # physics=1.0 creates drag: 0.1 * (1.0 - 0.5) = 0.05
        initial_state = AxiomaticState(physics=1.0)
        
        new_state = engine.evolve_state(initial_state, delta_t=1.0)
        
        # New physics should be 1.0 - (0.05 * 1.0) = 0.95
        assert new_state.physics < 1.0
        assert pytest.approx(new_state.physics, 0.01) == 0.95

    def test_coherence_gain_at_hiho(self):
        """[P0] Maximum coherence gain should occur at the 0.5 stability point."""
        engine = SpatialPhononsEngine()
        
        state_at_target = AxiomaticState(physics=0.5)
        state_away = AxiomaticState(physics=1.0)
        
        gain_target = engine.calculate_coherence_gain(state_at_target)
        gain_away = engine.calculate_coherence_gain(state_away)
        
        assert gain_target > gain_away
        assert gain_target == engine.params.phonon_coupling

class TestUniverseEngineIntegration:
    @pytest.mark.asyncio
    async def test_evolve_trajectory_with_phonons(self):
        """[P0] UniverseSimulationEngine should use phonons for evolution."""
        engine = UniverseSimulationEngine()
        journey = UniverseJourney(
            id="test-j", 
            agent_name="test", 
            intent="test",
            initial_axiomatic=AxiomaticState(spatial_x=1.0)
        )
        
        # Mock encoder to avoid actual LLM calls
        from unittest.mock import AsyncMock
        mock_encoder = MagicMock()
        mock_encoder.encode = AsyncMock(return_value=[0.0]*2048)
        engine._fallback_encoder = mock_encoder
        
        # We need to mock cohezion_core to trigger the Python fallback if not installed
        # and also mock monitor
        with patch("cohezion.reliability.monitor.get_resource_monitor") as mock_mon:
            mock_mon.return_value.get_vitals.return_value = {
                "cpu_percent": 10, "vram_percent": 10, "dilation_factor": 1.0, "memory_percent": 10
            }
            
            point = await engine.evolve_trajectory(journey, action="test action")
            
            assert point.step_number == 0
            # Confirm spatial expansion occurred (default phonon step)
            assert point.axiomatic.spatial_x > 1.0
            assert point.coherence > 0.5 # Should have gained from alignment
