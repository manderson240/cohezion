"""Tests for the universe simulation engine (cohezion.universe.engine)."""

from __future__ import annotations

import json
import time

import pytest

from cohezion.universe.engine import (
    AxiomaticState,
    LatentState,
    SimpleEncoder,
    TrajectoryPoint,
    UniverseJourney,
    UniverseSimulationEngine,
)


# ---------------------------------------------------------------------------
# AxiomaticState tests
# ---------------------------------------------------------------------------


class TestAxiomaticState:
    def test_default_values(self):
        state = AxiomaticState()
        assert state.spatial_x == 0.0
        assert state.physics == 0.5
        assert state.precipitation == 0.0

    def test_to_vector_length(self):
        state = AxiomaticState()
        vec = state.to_vector()
        assert len(vec) == 12

    def test_to_vector_values(self):
        state = AxiomaticState(spatial_x=1.0, spatial_y=2.0, spatial_z=3.0)
        vec = state.to_vector()
        assert vec[0] == 1.0
        assert vec[1] == 2.0
        assert vec[2] == 3.0

    def test_from_vector_roundtrip(self):
        original = AxiomaticState(spatial_x=1.0, physics=0.7, novelty=0.3)
        vec = original.to_vector()
        restored = AxiomaticState.from_vector(vec)
        assert restored.spatial_x == 1.0
        assert restored.physics == 0.7
        assert restored.novelty == 0.3

    def test_coherence_score_perfect_at_half(self):
        """All dimensions at 0.5 should give perfect coherence (1.0)."""
        state = AxiomaticState(
            physics=0.5,
            biology=0.5,
            logic=0.5,
            quantum=0.5,
            field=0.5,
            control=0.5,
            novelty=0.5,
        )
        assert state.coherence_score() == 1.0

    def test_coherence_score_decays_away_from_half(self):
        """Dimensions far from 0.5 should give lower coherence."""
        state = AxiomaticState(
            physics=0.0,
            biology=0.0,
            logic=0.0,
            quantum=0.0,
            field=0.0,
            control=0.0,
            novelty=0.0,
        )
        score = state.coherence_score()
        assert score < 1.0
        assert score >= 0.0

    def test_coherence_extremes(self):
        """All dimensions at 1.0 should be well below perfect coherence."""
        state = AxiomaticState(
            physics=1.0,
            biology=1.0,
            logic=1.0,
            quantum=1.0,
            field=1.0,
            control=1.0,
            novelty=1.0,
        )
        score = state.coherence_score()
        assert score < 1.0


# ---------------------------------------------------------------------------
# LatentState tests
# ---------------------------------------------------------------------------


class TestLatentState:
    def test_padding_to_2048(self):
        state = LatentState(embedding=[1.0] * 100, semantic_intent="test")
        assert len(state.embedding) == 2048
        assert state.embedding[0] == 1.0
        assert state.embedding[100] == 0.0  # Padded

    def test_truncating_to_2048(self):
        state = LatentState(embedding=[0.5] * 3000, semantic_intent="test")
        assert len(state.embedding) == 2048

    def test_exact_2048_unchanged(self):
        vec = [0.1] * 2048
        state = LatentState(embedding=vec, semantic_intent="test")
        assert len(state.embedding) == 2048
        assert state.embedding == vec


# ---------------------------------------------------------------------------
# UniverseJourney tests
# ---------------------------------------------------------------------------


class TestUniverseJourney:
    def test_add_trajectory_point(self):
        journey = UniverseJourney(id="j1", agent_name="TestAgent", intent="test")
        point = TrajectoryPoint(
            step_number=0,
            timestamp=time.time(),
            axiomatic=AxiomaticState(),
            latent=LatentState([0.0] * 2048, "test"),
            coherence=0.95,
            action_taken="test_action",
        )
        journey.add_trajectory_point(point)
        assert len(journey.trajectory) == 1
        assert journey.final_coherence == 0.95

    def test_complete(self):
        journey = UniverseJourney(id="j2", agent_name="TestAgent", intent="test")
        journey.complete(precipitation={"code": "print('hi')"}, phi_score=0.85)
        assert journey.status == "completed"
        assert journey.final_phi_score == 0.85
        assert journey.completed_at is not None

    def test_to_dict(self):
        journey = UniverseJourney(id="j3", agent_name="TestAgent", intent="test")
        d = journey.to_dict()
        assert d["id"] == "j3"
        assert d["agent_name"] == "TestAgent"
        assert d["intent"] == "test"
        assert d["status"] == "active"
        assert d["trajectory_count"] == 0
        assert "created_at" in d

    def test_to_dict_completed(self):
        journey = UniverseJourney(id="j4", agent_name="A", intent="t")
        journey.complete({"out": "data"}, phi_score=0.9)
        d = journey.to_dict()
        assert d["status"] == "completed"
        assert d["completed_at"] is not None


# ---------------------------------------------------------------------------
# SimpleEncoder tests
# ---------------------------------------------------------------------------


class TestSimpleEncoder:
    @pytest.mark.asyncio
    async def test_encode_returns_2048d(self):
        encoder = SimpleEncoder()
        vec = await encoder.encode("hello world")
        assert len(vec) == 2048

    @pytest.mark.asyncio
    async def test_encode_deterministic(self):
        encoder = SimpleEncoder()
        v1 = await encoder.encode("test string")
        v2 = await encoder.encode("test string")
        assert v1 == v2

    @pytest.mark.asyncio
    async def test_encode_different_inputs(self):
        encoder = SimpleEncoder()
        v1 = await encoder.encode("hello")
        v2 = await encoder.encode("world")
        assert v1 != v2

    @pytest.mark.asyncio
    async def test_encode_values_in_range(self):
        encoder = SimpleEncoder()
        vec = await encoder.encode("test")
        assert all(0.0 <= v <= 1.0 for v in vec)


# ---------------------------------------------------------------------------
# UniverseSimulationEngine tests
# ---------------------------------------------------------------------------


class TestUniverseSimulationEngine:
    def test_init_creates_storage(self, tmp_path):
        storage = tmp_path / "universe"
        UniverseSimulationEngine(local_storage_path=storage)
        assert storage.exists()

    def test_toward_target(self, tmp_path):
        engine = UniverseSimulationEngine(local_storage_path=tmp_path / "u")
        # Moving from 0.0 toward 0.5 with factor 1.0
        result = engine._toward_target(0.0, 0.5, 1.0)
        assert result == 0.25  # 0.0 + 0.5 * 1.0 * 0.5

    def test_toward_target_already_at_target(self, tmp_path):
        engine = UniverseSimulationEngine(local_storage_path=tmp_path / "u")
        result = engine._toward_target(0.5, 0.5, 1.0)
        assert result == 0.5

    def test_toward_target_zero_factor(self, tmp_path):
        engine = UniverseSimulationEngine(local_storage_path=tmp_path / "u")
        result = engine._toward_target(0.0, 1.0, 0.0)
        assert result == 0.0

    def test_extract_knowledge_high_phi(self, tmp_path):
        engine = UniverseSimulationEngine(local_storage_path=tmp_path / "u")
        journey = UniverseJourney(id="ek1", agent_name="A", intent="test")
        journey.final_phi_score = 0.9
        journey.final_coherence = 0.85
        knowledge = engine._extract_knowledge(journey)
        assert any(k["type"] == "success_pattern" for k in knowledge)

    def test_extract_knowledge_low_phi(self, tmp_path):
        engine = UniverseSimulationEngine(local_storage_path=tmp_path / "u")
        journey = UniverseJourney(id="ek2", agent_name="A", intent="test")
        journey.final_phi_score = 0.3
        knowledge = engine._extract_knowledge(journey)
        assert not any(k["type"] == "success_pattern" for k in knowledge)

    def test_extract_knowledge_long_trajectory(self, tmp_path):
        engine = UniverseSimulationEngine(local_storage_path=tmp_path / "u")
        journey = UniverseJourney(id="ek3", agent_name="A", intent="test")
        for i in range(5):
            point = TrajectoryPoint(
                step_number=i,
                timestamp=time.time(),
                axiomatic=AxiomaticState(),
                latent=LatentState([0.0] * 2048, "t"),
                coherence=0.8,
                action_taken="step",
            )
            journey.add_trajectory_point(point)
        knowledge = engine._extract_knowledge(journey)
        assert any(k["type"] == "process_pattern" for k in knowledge)

    @pytest.mark.asyncio
    async def test_persist_journey_local(self, tmp_path):
        storage = tmp_path / "universe"
        engine = UniverseSimulationEngine(local_storage_path=storage)
        journey = UniverseJourney(id="pj1", agent_name="A", intent="test")
        await engine._persist_journey(journey)

        filepath = storage / "pj1.json"
        assert filepath.exists()
        data = json.loads(filepath.read_text())
        assert data["id"] == "pj1"

    @pytest.mark.asyncio
    async def test_find_similar_journeys_empty(self, tmp_path):
        storage = tmp_path / "universe"
        engine = UniverseSimulationEngine(local_storage_path=storage)
        results = await engine.find_similar_journeys([0.1] * 512)
        assert results == []

    @pytest.mark.asyncio
    async def test_get_experience_replay_no_similar(self, tmp_path):
        storage = tmp_path / "universe"
        engine = UniverseSimulationEngine(local_storage_path=storage)
        result = await engine.get_experience_replay("find nothing")
        assert "No previous experience" in result
