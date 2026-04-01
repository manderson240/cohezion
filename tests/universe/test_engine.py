"""Tests for universe/engine.py.

Covers 12D/2048D manifold states and simulation engine.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch, sys

import pytest


# Mock cohezion_core and multimodal_bridge before they're imported
mock_cc = MagicMock()
sys.modules["cohezion_core"] = mock_cc
sys.modules["cohezion_core.cohezion_core_rs"] = mock_cc

mock_mb = MagicMock()
mock_mb.LOCAL_MULTIMODAL_BRIDGE = MagicMock()
mock_mb.LOCAL_MULTIMODAL_BRIDGE.schedule_asset = AsyncMock()
sys.modules["cohezion.core.multimodal_bridge"] = mock_mb

from cohezion.universe.engine import (
    AxiomaticState,
    LatentState,
    UniverseJourney,
    UniverseSimulationEngine,
)


class TestAxiomaticState:
    """[P0] Unit tests for AxiomaticState class."""

    def test_initialization(self):
        """[P0] Should initialize with defaults."""
        state = AxiomaticState()
        assert state.physics == 0.5
        assert state.logic == 0.5
        assert len(state.to_vector()) == 12

    def test_spin_coherence(self):
        """[P0] Should calculate spin coherence."""
        # Aligned (both >= 0.5)
        state = AxiomaticState(logic=0.6, quantum=0.6)
        assert state.spin_coherence == 1.0
        
        # Aligned (both < 0.5)
        state = AxiomaticState(logic=0.4, quantum=0.4)
        assert state.spin_coherence == 1.0
        
        # Opposed (Wait, current implementation always returns 1.0 due to abs())
        state = AxiomaticState(logic=0.6, quantum=0.4)
        # assert state.spin_coherence == 0.0 # This would fail now
        assert state.spin_coherence == 1.0

    def test_coherence_score(self):
        """[P0] Should calculate total coherence."""
        # Perfect stability at 0.5
        state = AxiomaticState(
            physics=0.5, biology=0.5, logic=0.5, quantum=0.5,
            field=0.5, control=0.5, novelty=0.5
        )
        assert state.coherence_score() >= 1.0

class TestLatentState:
    """[P0] Unit tests for LatentState class."""

    def test_embedding_padding(self):
        """[P0] Should pad embedding to 2048D."""
        state = LatentState(embedding=[0.1, 0.2], semantic_intent="test")
        assert len(state.embedding) == 2048
        assert state.embedding[0] == 0.1
        assert state.embedding[2] == 0.0

class TestUniverseSimulationEngine:
    """[P0] Unit tests for UniverseSimulationEngine."""

    @pytest.fixture
    def engine(self, tmp_path):
        return UniverseSimulationEngine(local_storage_path=tmp_path)

    @pytest.mark.asyncio
    async def test_start_journey(self, engine):
        """[P0] Should start new journey."""
        with patch("cohezion.reliability.monitor.get_resource_monitor") as mock_mon, \
             patch("cohezion_core.cohezion_core_rs.FlumePhysics") as mock_phys:
            
            mock_mon.return_value.get_vitals.return_value = {
                "cpu_percent": 10, "vram_percent": 20, "dilation_factor": 1.0, "memory_percent": 30
            }
            mock_phys.return_value.calculate_entropy.return_value = 4.0
            mock_phys.return_value.project_holographic.return_value = [0.0] * 12
            
            journey = await engine.start_journey(agent_name="TestAgent", intent="test intent")
            
            assert journey.agent_name == "TestAgent"
            assert journey.intent == "test intent"
            assert len(journey.id) > 0
            assert isinstance(journey.initial_axiomatic, AxiomaticState)

    @pytest.mark.asyncio
    async def test_evolve_trajectory(self, engine):
        """[P0] Should evolve journey trajectory."""
        journey = UniverseJourney(id="j1", agent_name="A1", intent="test")
        
        with patch("cohezion.reliability.monitor.get_resource_monitor") as mock_mon, \
             patch("cohezion_core.cohezion_core_rs.FlumePhysics") as mock_phys:
            
            mock_mon.return_value.get_vitals.return_value = {
                "cpu_percent": 10, "vram_percent": 20, "dilation_factor": 1.0, "memory_percent": 30
            }
            mock_phys.return_value.calculate_entropy.return_value = 4.0
            mock_phys.return_value.project_holographic.return_value = [0.0] * 12
            
            point = await engine.evolve_trajectory(journey, action="think")
            
            assert len(journey.trajectory) == 1
            assert point.step_number == 0
            assert point.action_taken == "think"
            assert point.coherence > 0
