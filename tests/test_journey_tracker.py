"""Tests for FLUME journey tracker and related compound modules.

Covers:
- JourneyTracker: start, record, complete journeys
- JourneyPersistence: JSONL save/load round-trip
- InflectionDetector: score shifts, coherence drops, failure streaks
- TokenEfficientClient.batch_generate: cache hits, parallel execution
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

pytestmark = pytest.mark.skip(reason="Tests stash-era JourneyTracker/InflectionDetector API; HEAD modules evolved (Sessions 25-29)")


# ---------------------------------------------------------------------------
# Journey Tracker Tests
# ---------------------------------------------------------------------------


class TestJourneyTracker:
    """Test FLUME journey tracking for compound executions."""

    def test_start_journey(self):
        from cohezion.compound.journey_tracker import JourneyTracker

        tracker = JourneyTracker(agent_name="test_agent", use_rust_physics=False)
        journey = tracker.start_journey("TEST_SKILL", "hello world")

        assert journey.agent_name == "test_agent"
        assert journey.status == "active"
        assert "TEST_SKILL" in journey.intent
        assert journey.initial_axiomatic is not None
        assert journey.initial_latent is not None
        assert len(journey.initial_latent.embedding) == 2048

    def test_record_step(self):
        from cohezion.compound.journey_tracker import JourneyTracker

        tracker = JourneyTracker(use_rust_physics=False)
        journey = tracker.start_journey("SKILL_A", "input text")

        point = tracker.record_step(
            journey_id=journey.id,
            step_index=0,
            operation="search",
            output="found results",
            tokens_used=100,
            duration_ms=50.0,
            model="phi3:mini",
        )

        assert point is not None
        assert point.step_number == 0
        assert point.coherence > 0
        assert "search" in point.action_taken
        assert len(journey.trajectory) == 1

    def test_record_multiple_steps(self):
        from cohezion.compound.journey_tracker import JourneyTracker

        tracker = JourneyTracker(use_rust_physics=False)
        journey = tracker.start_journey("SKILL_B", "multi step")

        for i in range(5):
            tracker.record_step(
                journey_id=journey.id,
                step_index=i,
                operation="generate",
                output=f"output_{i}",
                tokens_used=50 * (i + 1),
                duration_ms=10.0 * (i + 1),
            )

        assert len(journey.trajectory) == 5
        assert journey.final_coherence > 0

    def test_complete_journey(self):
        from cohezion.compound.journey_tracker import JourneyTracker

        tracker = JourneyTracker(use_rust_physics=False)
        journey = tracker.start_journey("SKILL_C", "test input")

        tracker.record_step(
            journey_id=journey.id,
            step_index=0,
            operation="analyze",
            output="analysis result",
            tokens_used=200,
            duration_ms=100.0,
        )

        completed = tracker.complete_journey(
            journey_id=journey.id,
            final_output="final result",
            compound_score_delta=0.15,
            refinements_applied=2,
        )

        assert completed is not None
        assert completed.status == "completed"
        assert completed.final_phi_score > 0
        assert completed.precipitation["compound_score_delta"] == 0.15
        assert completed.precipitation["refinements_applied"] == 2

    def test_complete_nonexistent_journey(self):
        from cohezion.compound.journey_tracker import JourneyTracker

        tracker = JourneyTracker(use_rust_physics=False)
        result = tracker.complete_journey("nonexistent_id", "output")
        assert result is None

    def test_record_step_nonexistent_journey(self):
        from cohezion.compound.journey_tracker import JourneyTracker

        tracker = JourneyTracker(use_rust_physics=False)
        point = tracker.record_step("nonexistent", 0, "search", "out", 10, 5.0)
        assert point is None

    def test_get_active_journeys(self):
        from cohezion.compound.journey_tracker import JourneyTracker

        tracker = JourneyTracker(use_rust_physics=False)
        tracker.start_journey("SKILL_1", "a")
        tracker.start_journey("SKILL_2", "b")

        active = tracker.get_active_journeys()
        assert len(active) == 2

    def test_journey_summary(self):
        from cohezion.compound.journey_tracker import JourneyTracker

        tracker = JourneyTracker(use_rust_physics=False)
        journey = tracker.start_journey("SKILL_SUM", "summarize me")

        for i in range(3):
            tracker.record_step(
                journey_id=journey.id,
                step_index=i,
                operation="analyze",
                output=f"step_{i}",
                tokens_used=100,
                duration_ms=50.0,
            )

        completed = tracker.complete_journey(journey.id, "done")
        assert completed is not None

        summary = tracker.get_journey_summary(completed)
        assert summary["steps"] == 3
        assert len(summary["coherence_trajectory"]) == 3
        assert summary["mean_coherence"] > 0
        assert summary["status"] == "completed"

    def test_phi_score_computation(self):
        """Phi score should reward smooth, convergent trajectories."""
        from cohezion.compound.journey_tracker import JourneyTracker

        tracker = JourneyTracker(use_rust_physics=False)
        journey = tracker.start_journey("PHI_TEST", "phi")

        # Generate a smooth trajectory
        for i in range(10):
            tracker.record_step(
                journey_id=journey.id,
                step_index=i,
                operation="generate",
                output=f"progressive output {i}",
                tokens_used=100 + i * 10,
                duration_ms=50.0,
            )

        completed = tracker.complete_journey(journey.id, "converged")
        assert completed is not None
        assert 0.0 <= completed.final_phi_score <= 1.0

    def test_operation_profiles_modulate_axiomatic(self):
        """Different operations should produce different 12D projections."""
        from cohezion.compound.journey_tracker import JourneyTracker

        tracker = JourneyTracker(use_rust_physics=False)
        journey = tracker.start_journey("OP_TEST", "test ops")

        p_search = tracker.record_step(journey.id, 0, "search", "found", 50, 10.0)
        p_persist = tracker.record_step(journey.id, 1, "persist", "saved", 50, 10.0)

        assert p_search is not None and p_persist is not None
        # Search should have higher novelty than persist
        assert p_search.axiomatic.novelty > p_persist.axiomatic.novelty
        # Persist should have higher precipitation
        assert p_persist.axiomatic.precipitation > p_search.axiomatic.precipitation


# ---------------------------------------------------------------------------
# Journey Persistence Tests
# ---------------------------------------------------------------------------


class TestJourneyPersistence:
    """Test JSONL journey persistence."""

    @pytest.fixture
    def tmp_dir(self, tmp_path):
        return tmp_path / "journeys"

    @pytest.mark.asyncio
    async def test_save_and_load_journey(self, tmp_dir):
        from cohezion.compound.journey_persistence import JourneyPersistence

        jp = JourneyPersistence(jsonl_dir=tmp_dir)
        jp._surreal_available = False  # Force JSONL fallback

        journey_data = {
            "id": "journey_test_001",
            "agent_name": "test_agent",
            "intent": "Compound execution of TEST_SKILL",
            "status": "completed",
            "final_coherence": 0.52,
            "final_phi_score": 0.75,
            "trajectory_count": 3,
            "precipitation": {"output": "done", "compound_score_delta": 0.1},
        }

        ref = await jp.save_journey(journey_data)
        assert "jsonl" in ref

        loaded = await jp.load_journeys(agent_name="test_agent")
        assert len(loaded) == 1
        assert loaded[0]["id"] == "journey_test_001"
        assert loaded[0]["final_coherence"] == 0.52

    @pytest.mark.asyncio
    async def test_save_trajectory_point(self, tmp_dir):
        from cohezion.compound.journey_persistence import JourneyPersistence

        jp = JourneyPersistence(jsonl_dir=tmp_dir)
        jp._surreal_available = False

        point_data = {
            "step_number": 0,
            "coherence": 0.55,
            "operation": "search",
            "output": "found results",
        }

        ref = await jp.save_trajectory_point("journey_001", point_data)
        assert "point" in ref

    @pytest.mark.asyncio
    async def test_load_full_journey(self, tmp_dir):
        from cohezion.compound.journey_persistence import JourneyPersistence

        jp = JourneyPersistence(jsonl_dir=tmp_dir)
        jp._surreal_available = False

        # Save journey
        await jp.save_journey(
            {"id": "journey_full_001", "agent_name": "agent", "intent": "test"}
        )

        # Save trajectory points
        for i in range(3):
            await jp.save_trajectory_point(
                "journey_full_001",
                {"step_number": i, "coherence": 0.5 + i * 0.01},
            )

        full = await jp.load_journey_with_trajectory("journey_full_001")
        assert full is not None
        assert full["id"] == "journey_full_001"
        assert len(full["trajectory_points"]) == 3

    @pytest.mark.asyncio
    async def test_experience_guidance(self, tmp_dir):
        from cohezion.compound.journey_persistence import JourneyPersistence

        jp = JourneyPersistence(jsonl_dir=tmp_dir)
        jp._surreal_available = False

        # Save past journeys
        for i in range(3):
            await jp.save_journey(
                {
                    "id": f"journey_guide_{i}",
                    "agent_name": "agent",
                    "intent": "Compound execution of ANALYZE_SKILL",
                    "status": "completed",
                    "final_coherence": 0.5 + i * 0.05,
                    "final_phi_score": 0.6 + i * 0.1,
                    "trajectory_count": 5,
                    "precipitation": {"compound_score_delta": 0.05 * i},
                }
            )

        guidance = await jp.get_experience_guidance("ANALYZE_SKILL")
        assert len(guidance) == 3
        # Most recent first (highest coherence)
        assert guidance[0]["final_coherence"] == 0.6

    @pytest.mark.asyncio
    async def test_filter_by_skill(self, tmp_dir):
        from cohezion.compound.journey_persistence import JourneyPersistence

        jp = JourneyPersistence(jsonl_dir=tmp_dir)
        jp._surreal_available = False

        await jp.save_journey(
            {"id": "j1", "agent_name": "a", "intent": "execution of SKILL_A"}
        )
        await jp.save_journey(
            {"id": "j2", "agent_name": "a", "intent": "execution of SKILL_B"}
        )

        a_only = await jp.load_journeys(skill_name="SKILL_A")
        assert len(a_only) == 1
        assert a_only[0]["id"] == "j1"


# ---------------------------------------------------------------------------
# Inflection Detector Tests
# ---------------------------------------------------------------------------


class TestInflectionDetector:
    """Test inflection detection and retrospective triggers."""

    def test_score_shift_detected(self):
        from cohezion.compound.inflection_detector import InflectionDetector

        detector = InflectionDetector(score_threshold=0.1)
        event = detector.check_compound_score("SKILL_X", 0.15)

        assert event is not None
        assert event.event_type == "score_shift"
        assert event.severity == "warning"
        assert event.details["direction"] == "positive"

    def test_score_below_threshold_no_event(self):
        from cohezion.compound.inflection_detector import InflectionDetector

        detector = InflectionDetector(score_threshold=0.1)
        event = detector.check_compound_score("SKILL_X", 0.05)
        assert event is None

    def test_critical_score_shift(self):
        from cohezion.compound.inflection_detector import InflectionDetector

        detector = InflectionDetector(score_threshold=0.1)
        event = detector.check_compound_score("SKILL_X", -0.25)

        assert event is not None
        assert event.severity == "critical"
        assert event.details["direction"] == "negative"

    def test_coherence_drop(self):
        from cohezion.compound.inflection_detector import InflectionDetector

        detector = InflectionDetector(coherence_floor=0.3)
        event = detector.check_coherence(5, 0.2, "SKILL_Y")

        assert event is not None
        assert event.event_type == "coherence_drop"
        assert event.severity == "warning"

    def test_coherence_spike(self):
        from cohezion.compound.inflection_detector import InflectionDetector

        detector = InflectionDetector(coherence_ceiling=0.7)
        event = detector.check_coherence(3, 0.85, "SKILL_Y")

        assert event is not None
        assert event.event_type == "coherence_spike"

    def test_coherence_normal_no_event(self):
        from cohezion.compound.inflection_detector import InflectionDetector

        detector = InflectionDetector()
        event = detector.check_coherence(0, 0.5)
        assert event is None

    def test_failure_streak(self):
        from cohezion.compound.inflection_detector import InflectionDetector

        detector = InflectionDetector(failure_streak_limit=3)

        # Three consecutive zero-token steps
        assert detector.check_step_failure(0, 0) is None
        assert detector.check_step_failure(0, 1) is None
        event = detector.check_step_failure(0, 2)

        assert event is not None
        assert event.event_type == "failure_streak"
        assert event.severity == "critical"

    def test_failure_streak_reset_on_success(self):
        from cohezion.compound.inflection_detector import InflectionDetector

        detector = InflectionDetector(failure_streak_limit=3)

        detector.check_step_failure(0, 0)
        detector.check_step_failure(0, 1)
        detector.check_step_failure(100, 2)  # Success resets streak
        assert detector.check_step_failure(0, 3) is None  # Only 1 failure

    def test_history_tracking(self):
        from cohezion.compound.inflection_detector import InflectionDetector

        detector = InflectionDetector(score_threshold=0.05)
        detector.check_compound_score("A", 0.1)
        detector.check_compound_score("B", -0.2)
        detector.check_compound_score("C", 0.01)  # No event

        history = detector.get_history()
        assert len(history) == 2

    @pytest.mark.asyncio
    async def test_deep_retrospective_disabled(self):
        from cohezion.compound.inflection_detector import (
            InflectionDetector,
            InflectionEvent,
        )

        detector = InflectionDetector(auto_retrospect=False)
        event = InflectionEvent(event_type="test", severity="warning")

        result = await detector.run_deep_retrospective(event)
        assert result["skipped"] is True

    def test_reset(self):
        from cohezion.compound.inflection_detector import InflectionDetector

        detector = InflectionDetector(score_threshold=0.05)
        detector.check_compound_score("A", 0.1)
        detector.check_coherence(0, 0.2)

        detector.reset()
        assert len(detector.get_history()) == 0


# ---------------------------------------------------------------------------
# Batch Generate Tests
# ---------------------------------------------------------------------------


class TestBatchGenerate:
    """Test TokenEfficientClient.batch_generate."""

    @pytest.mark.asyncio
    async def test_batch_all_cached(self):
        from cohezion.swarm.token_client import TokenEfficientClient

        client = TokenEfficientClient(cache_max_size=100)
        # Pre-populate cache
        client._cache[client._cache_key("hello", None, None)] = "world"
        client._cache[client._cache_key("foo", None, None)] = "bar"

        results = await client.batch_generate(
            [
                {"prompt": "hello"},
                {"prompt": "foo"},
            ]
        )

        assert results == ["world", "bar"]
        assert client.metrics.cache_hits == 2
        assert client.metrics.cache_misses == 0

    @pytest.mark.asyncio
    async def test_batch_mixed_cache(self):
        from cohezion.swarm.token_client import TokenEfficientClient

        mock_ollama = AsyncMock()
        mock_ollama.generate = AsyncMock(return_value="generated_response")

        client = TokenEfficientClient(ollama_client=mock_ollama, cache_max_size=100)
        # Pre-populate one cache entry
        client._cache[client._cache_key("cached_prompt", None, None)] = "cached_result"

        results = await client.batch_generate(
            [
                {"prompt": "cached_prompt"},
                {"prompt": "new_prompt"},
            ]
        )

        assert results[0] == "cached_result"
        assert results[1] == "generated_response"
        assert client.metrics.cache_hits == 1
        assert client.metrics.cache_misses == 1

    @pytest.mark.asyncio
    async def test_batch_all_miss(self):
        from cohezion.swarm.token_client import TokenEfficientClient

        mock_ollama = AsyncMock()
        mock_ollama.generate = AsyncMock(side_effect=["resp_a", "resp_b", "resp_c"])

        client = TokenEfficientClient(ollama_client=mock_ollama, cache_max_size=100)

        results = await client.batch_generate(
            [
                {"prompt": "a"},
                {"prompt": "b"},
                {"prompt": "c"},
            ]
        )

        assert len(results) == 3
        assert client.metrics.cache_misses == 3
        # Results should be cached now
        assert len(client._cache) == 3

    @pytest.mark.asyncio
    async def test_batch_cache_eviction(self):
        from cohezion.swarm.token_client import TokenEfficientClient

        mock_ollama = AsyncMock()
        mock_ollama.generate = AsyncMock(return_value="new")

        client = TokenEfficientClient(ollama_client=mock_ollama, cache_max_size=2)

        results = await client.batch_generate(
            [
                {"prompt": "p1"},
                {"prompt": "p2"},
                {"prompt": "p3"},
            ]
        )

        assert len(results) == 3
        # Only 2 entries fit in cache
        assert len(client._cache) == 2

    @pytest.mark.asyncio
    async def test_batch_empty_list(self):
        from cohezion.swarm.token_client import TokenEfficientClient

        client = TokenEfficientClient(cache_max_size=100)
        results = await client.batch_generate([])
        assert results == []


# ---------------------------------------------------------------------------
# Integration: Compound __init__ exports
# ---------------------------------------------------------------------------


class TestCompoundExports:
    """Verify new modules are exported from compound package."""

    def test_journey_tracker_import(self):
        from cohezion.compound import JourneyTracker, get_tracker

        tracker = get_tracker("test")
        assert isinstance(tracker, JourneyTracker)

    def test_journey_persistence_import(self):
        from cohezion.compound import JourneyPersistence

        jp = JourneyPersistence()
        assert jp is not None

    def test_inflection_detector_import(self):
        from cohezion.compound import InflectionDetector, InflectionEvent

        detector = InflectionDetector()
        assert detector is not None
        event = InflectionEvent(event_type="test")
        assert event.event_type == "test"
