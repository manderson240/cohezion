"""Tests for journey tracking with 12D FLUME trajectories."""

import numpy as np
import pytest

from cohezion.compound.executor import ExecutionResult
from cohezion.compound.journey_tracker import (
    Journey,
    JourneyTracker,
    JourneyTrackerFactory,
    OperationType,
    TrajectoryPoint,
)


@pytest.fixture
def tracker():
    """Create a journey tracker."""
    return JourneyTracker(seed=42)


@pytest.fixture
def execution_result():
    """Create a mock execution result."""
    return ExecutionResult(
        success=True,
        output="test output",
        metrics={"coherence": 0.85},
        duration_seconds=1.5,
        token_metrics={"cache_hit_rate": 0.7},
    )


class TestOperationType:
    """Tests for OperationType enum."""

    def test_operation_type_values(self):
        """Test all operation types are defined."""
        assert OperationType.GENERATE.value == "generate"
        assert OperationType.ANALYZE.value == "analyze"
        assert OperationType.SEARCH.value == "search"
        assert OperationType.TRANSFORM.value == "transform"
        assert OperationType.PERSIST.value == "persist"


class TestTrajectoryPoint:
    """Tests for TrajectoryPoint dataclass."""

    def test_trajectory_point_creation(self):
        """Test creating a trajectory point."""
        point = TrajectoryPoint(
            dimensions=np.array([0.5] * 12),
            timestamp=1.5,
            coherence=0.85,
            efficiency=0.7,
            operation_type="generate",
            task_description="Test task",
        )

        assert point.timestamp == 1.5
        assert point.coherence == 0.85
        assert len(point.dimensions) == 12
        assert point.operation_type == "generate"

    def test_trajectory_point_with_metadata(self):
        """Test trajectory point with metadata."""
        point = TrajectoryPoint(
            dimensions=np.array([0.5] * 12),
            timestamp=1.5,
            coherence=0.85,
            efficiency=0.7,
            operation_type="generate",
            task_description="Test task",
            metadata={"phi_score": 0.82, "success": True},
        )

        assert point.metadata["phi_score"] == 0.82
        assert point.metadata["success"] is True


class TestJourney:
    """Tests for Journey dataclass."""

    def test_journey_creation(self):
        """Test creating a journey."""
        points = [
            TrajectoryPoint(
                dimensions=np.array([0.5] * 12),
                timestamp=1.5,
                coherence=0.85,
                efficiency=0.7,
                operation_type="generate",
                task_description="Test task",
            )
        ]

        journey = Journey(
            execution_id="exec_123",
            points=points,
            start_time=0.0,
            end_time=1.5,
            task_description="Test task",
            operation_type="generate",
            final_success=True,
            phi_score=0.82,
        )

        assert journey.execution_id == "exec_123"
        assert len(journey.points) == 1
        assert journey.final_success is True


class TestJourneyTrackerInitialization:
    """Tests for journey tracker initialization."""

    def test_initialization_default(self):
        """Test initialization with defaults."""
        tracker = JourneyTracker()

        assert tracker.seed == 42
        assert tracker.AXIOMATIC_DIMS == 12
        assert tracker.HASH_DIMS == 2048
        assert tracker.CHUNK_SIZE == 128

    def test_initialization_custom_seed(self):
        """Test initialization with custom seed."""
        tracker = JourneyTracker(seed=123)

        assert tracker.seed == 123

    def test_modulation_profiles_created(self):
        """Test modulation profiles are created."""
        tracker = JourneyTracker()

        assert len(tracker._modulation_profiles) == 5
        assert "generate" in tracker._modulation_profiles
        assert "analyze" in tracker._modulation_profiles
        assert "search" in tracker._modulation_profiles
        assert "transform" in tracker._modulation_profiles
        assert "persist" in tracker._modulation_profiles

        # Each profile should be 12D
        for profile in tracker._modulation_profiles.values():
            assert len(profile) == 12
            # Values should be in [0, 1]
            assert np.all(profile >= 0.0) and np.all(profile <= 1.0)


class TestTextToLatent:
    """Tests for text-to-latent embedding."""

    def test_text_to_latent_output_shape(self, tracker):
        """Test latent vector has correct shape."""
        latent = tracker.text_to_latent("test text")

        assert len(latent) == 2048
        assert isinstance(latent, np.ndarray)

    def test_text_to_latent_normalized(self, tracker):
        """Test latent vector is normalized."""
        latent = tracker.text_to_latent("test text")

        assert np.all(latent >= -1.0) and np.all(latent <= 1.0)

    def test_text_to_latent_deterministic(self, tracker):
        """Test same text produces same embedding."""
        latent1 = tracker.text_to_latent("test text")
        latent2 = tracker.text_to_latent("test text")

        np.testing.assert_array_almost_equal(latent1, latent2)

    def test_text_to_latent_different_text(self, tracker):
        """Test different text produces different embeddings."""
        latent1 = tracker.text_to_latent("test text 1")
        latent2 = tracker.text_to_latent("test text 2")

        # Should not be identical
        assert not np.allclose(latent1, latent2)


class TestHolographicProjection:
    """Tests for holographic projection."""

    def test_holographic_projection_output_shape(self, tracker):
        """Test projection output has correct shape."""
        latent = tracker.text_to_latent("test text")
        projection = tracker.holographic_project(latent)

        assert len(projection) == 12
        assert isinstance(projection, np.ndarray)

    def test_holographic_projection_normalized(self, tracker):
        """Test projection is normalized to [0, 1]."""
        latent = tracker.text_to_latent("test text")
        projection = tracker.holographic_project(latent)

        assert np.all(projection >= 0.0) and np.all(projection <= 1.0)

    def test_holographic_projection_deterministic(self, tracker):
        """Test same input produces same projection."""
        latent = tracker.text_to_latent("test text")
        proj1 = tracker.holographic_project(latent)
        proj2 = tracker.holographic_project(latent)

        np.testing.assert_array_almost_equal(proj1, proj2)

    def test_holographic_projection_caching(self, tracker):
        """Test projection results are cached."""
        latent = tracker.text_to_latent("test text")

        # First call
        proj1 = tracker.holographic_project(latent)

        # Should be in cache
        assert len(tracker._projection_cache) > 0

        # Second call should use cache
        proj2 = tracker.holographic_project(latent)

        np.testing.assert_array_equal(proj1, proj2)


class TestStepToAxiomatic:
    """Tests for axiomatic step modulation."""

    def test_step_to_axiomatic_output_shape(self, tracker):
        """Test axiomatic output has correct shape."""
        projection = np.random.rand(12)
        axiomatic = tracker._step_to_axiomatic(
            projection, "generate", coherence=0.85, efficiency=0.7
        )

        assert len(axiomatic) == 12

    def test_step_to_axiomatic_normalized(self, tracker):
        """Test axiomatic output is normalized."""
        projection = np.random.rand(12)
        axiomatic = tracker._step_to_axiomatic(
            projection, "generate", coherence=0.85, efficiency=0.7
        )

        assert np.all(axiomatic >= 0.0) and np.all(axiomatic <= 1.0)

    def test_step_to_axiomatic_generate_profile(self, tracker):
        """Test GENERATE profile emphasizes novelty and logic."""
        projection = np.zeros(12)
        axiomatic = tracker._step_to_axiomatic(
            projection, "generate", coherence=1.0, efficiency=1.0
        )

        # With max quality weight, should be close to modulation profile
        profile = tracker._modulation_profiles["generate"]
        # Some influence from quality weighting
        assert np.allclose(axiomatic, profile, atol=0.1)

    def test_step_to_axiomatic_analyze_profile(self, tracker):
        """Test ANALYZE profile emphasizes logic and field."""
        projection = np.zeros(12)
        axiomatic = tracker._step_to_axiomatic(projection, "analyze", coherence=1.0, efficiency=1.0)

        profile = tracker._modulation_profiles["analyze"]
        assert np.allclose(axiomatic, profile, atol=0.1)

    def test_step_to_axiomatic_operation_types(self, tracker):
        """Test all operation types work."""
        projection = np.random.rand(12)

        for op_type in ["generate", "analyze", "search", "transform", "persist"]:
            axiomatic = tracker._step_to_axiomatic(
                projection, op_type, coherence=0.8, efficiency=0.8
            )

            assert len(axiomatic) == 12
            assert np.all(axiomatic >= 0.0) and np.all(axiomatic <= 1.0)


class TestPhiScore:
    """Tests for phi score computation."""

    def test_phi_score_computation(self, tracker):
        """Test phi score is computed correctly."""
        phi = tracker._compute_phi_score(coherence=0.8, smoothness=0.6, convergence=0.7)

        # phi = coherence * 0.5 + smoothness * 0.3 + convergence * 0.2
        expected = 0.8 * 0.5 + 0.6 * 0.3 + 0.7 * 0.2
        assert np.isclose(phi, expected)

    def test_phi_score_normalized(self, tracker):
        """Test phi score is in [0, 1]."""
        phi = tracker._compute_phi_score(coherence=0.9, smoothness=0.95, convergence=0.85)

        assert 0.0 <= phi <= 1.0

    def test_phi_score_clipping(self, tracker):
        """Test phi score clips to [0, 1]."""
        phi = tracker._compute_phi_score(coherence=1.5, smoothness=1.2, convergence=1.0)

        assert 0.0 <= phi <= 1.0


class TestTrackExecution:
    """Tests for tracking executions."""

    def test_track_execution_basic(self, tracker, execution_result):
        """Test tracking a basic execution."""
        point = tracker.track_execution(
            execution_result=execution_result,
            task_description="Generate ideas",
            operation_type="generate",
        )

        assert isinstance(point, TrajectoryPoint)
        assert len(point.dimensions) == 12
        assert point.coherence == 0.85
        assert point.efficiency == 0.7
        assert point.operation_type == "generate"

    def test_track_execution_attaches_surprise_routing(
        self, tracker, execution_result, monkeypatch
    ):
        """When the JEPA model is trained, the surprise->action seam fires: each enriched
        point carries an advisory `surprise_routing` decision (mode + fleet tier)."""

        class _FakeTrainedJEPA:
            _trained = True

            def surprise_score(self, prev, action, nxt):
                return 0.5  # constant -> EWMA steady state

        monkeypatch.setattr(
            "cohezion.api.services.world_model._get_model",
            lambda: _FakeTrainedJEPA(),
        )
        # First call seeds _recent_points; enrichment needs a prior point.
        tracker.track_execution(execution_result, "first task", "generate")
        point = tracker.track_execution(execution_result, "second task", "generate")

        assert "jepa_surprise" in point.metadata
        routing = point.metadata.get("surprise_routing")
        assert routing is not None
        assert routing["mode"] in {"explore", "exploit"}
        assert routing["tier"] in {"npu", "igpu", "cpu"}
        # Router is instance-level so its EWMA scale persists across the trajectory.
        assert tracker._surprise_router is not None

    def test_track_execution_no_routing_when_untrained(
        self, tracker, execution_result, monkeypatch
    ):
        """Untrained model -> no surprise enrichment -> no routing hint (no-op, not fabricated)."""

        class _FakeUntrainedJEPA:
            _trained = False

            def surprise_score(self, prev, action, nxt):  # pragma: no cover - never called
                raise AssertionError("surprise_score must not run when untrained")

        monkeypatch.setattr(
            "cohezion.api.services.world_model._get_model",
            lambda: _FakeUntrainedJEPA(),
        )
        tracker.track_execution(execution_result, "first task", "generate")
        point = tracker.track_execution(execution_result, "second task", "generate")
        assert "surprise_routing" not in point.metadata

    def test_track_execution_with_no_token_metrics(self, tracker):
        """Test tracking without token metrics."""
        result = ExecutionResult(
            success=True,
            output="output",
            metrics={"coherence": 0.9},
            duration_seconds=1.0,
            token_metrics=None,
        )

        point = tracker.track_execution(
            execution_result=result,
            task_description="Test task",
            operation_type="analyze",
        )

        assert point.efficiency == 0.5  # Default

    def test_track_execution_different_operations(self, tracker, execution_result):
        """Test tracking different operation types."""
        for op_type in ["generate", "analyze", "search", "transform", "persist"]:
            point = tracker.track_execution(
                execution_result=execution_result,
                task_description="Test task",
                operation_type=op_type,
            )

            assert point.operation_type == op_type
            assert len(point.dimensions) == 12

    def test_track_execution_metadata(self, tracker, execution_result):
        """Test tracked execution has metadata."""
        point = tracker.track_execution(
            execution_result=execution_result,
            task_description="Test task",
            operation_type="generate",
        )

        assert point.metadata is not None
        assert "phi_score" in point.metadata
        assert "success" in point.metadata
        assert "output_length" in point.metadata


class TestTrajectoryQuality:
    """Tests for trajectory quality computation."""

    def test_compute_trajectory_quality_empty(self, tracker):
        """Test quality with empty trajectory."""
        quality = tracker.compute_trajectory_quality([])

        assert quality["mean_phi_score"] == 0.0
        assert quality["mean_coherence"] == 0.0
        assert quality["mean_efficiency"] == 0.0

    def test_compute_trajectory_quality_single_point(self, tracker, execution_result):
        """Test quality with single point."""
        point = tracker.track_execution(
            execution_result=execution_result,
            task_description="Test task",
            operation_type="generate",
        )

        quality = tracker.compute_trajectory_quality([point])

        assert 0.0 <= quality["mean_phi_score"] <= 1.0
        assert 0.0 <= quality["mean_coherence"] <= 1.0
        assert 0.0 <= quality["mean_efficiency"] <= 1.0
        assert 0.0 <= quality["smoothness"] <= 1.0
        assert 0.0 <= quality["convergence"] <= 1.0

    def test_compute_trajectory_quality_multiple_points(self, tracker, execution_result):
        """Test quality with multiple points."""
        points = [
            tracker.track_execution(
                execution_result=ExecutionResult(
                    success=True,
                    output="output",
                    metrics={"coherence": 0.8 + 0.05 * i},
                    duration_seconds=1.0,
                    token_metrics={"cache_hit_rate": 0.6 + 0.05 * i},
                ),
                task_description=f"Task {i}",
                operation_type="generate",
            )
            for i in range(5)
        ]

        quality = tracker.compute_trajectory_quality(points)

        # Should have reasonable metrics
        assert quality["mean_phi_score"] > 0.0
        assert quality["mean_coherence"] > 0.7
        assert quality["smoothness"] > 0.0


class TestJourneyTrackerFactory:
    """Tests for factory pattern."""

    def test_factory_creates_tracker(self):
        """Test factory creates tracker."""
        tracker = JourneyTrackerFactory.create()

        assert isinstance(tracker, JourneyTracker)
        assert tracker.seed == 42

    def test_factory_custom_seed(self):
        """Test factory with custom seed."""
        tracker = JourneyTrackerFactory.create(seed=123)

        assert tracker.seed == 123


class TestDeterminism:
    """Tests for deterministic behavior across instances."""

    def test_same_seed_same_results(self):
        """Test two trackers with same seed produce same results."""
        tracker1 = JourneyTracker(seed=42)
        tracker2 = JourneyTracker(seed=42)

        text = "test text for determinism"
        latent1 = tracker1.text_to_latent(text)
        latent2 = tracker2.text_to_latent(text)

        np.testing.assert_array_equal(latent1, latent2)

    def test_different_seed_different_cache(self):
        """Test different seeds create separate caches."""
        tracker1 = JourneyTracker(seed=42)
        tracker2 = JourneyTracker(seed=123)

        # Cache should be separate
        assert tracker1._projection_cache is not tracker2._projection_cache


class TestIntegration:
    """Integration tests for journey tracking."""

    def test_full_tracking_pipeline(self, execution_result):
        """Test complete tracking pipeline."""
        tracker = JourneyTrackerFactory.create(seed=42)

        # Track multiple executions
        points = [
            tracker.track_execution(
                execution_result=ExecutionResult(
                    success=True,
                    output="output",
                    metrics={"coherence": 0.8 + 0.02 * i},
                    duration_seconds=1.0,
                    token_metrics={"cache_hit_rate": 0.6 + 0.02 * i},
                ),
                task_description=f"Generate {i}",
                operation_type="generate",
            )
            for i in range(10)
        ]

        # Compute journey quality
        quality = tracker.compute_trajectory_quality(points)

        # Should have meaningful metrics
        assert len(points) == 10
        assert quality["mean_coherence"] > 0.75
        assert quality["smoothness"] > 0.0
        assert quality["convergence"] > 0.0


# ---- Phase 4: Real smoothness/convergence for phi_score ----


class TestRealPhiScore:
    """Tests for real smoothness/convergence in phi_score (Phase 4)."""

    def test_phi_score_differs_after_5_executions(self):
        """phi_score differs from hardcoded calculation after 5+ executions."""
        tracker = JourneyTracker(seed=42)
        hardcoded_phi = tracker._compute_phi_score(0.85, 0.5, 0.5)

        # Track 5 similar executions
        for i in range(5):
            result = ExecutionResult(
                success=True,
                output="output",
                metrics={"coherence": 0.85},
                duration_seconds=1.0,
                token_metrics={"cache_hit_rate": 0.7},
            )
            point = tracker.track_execution(result, f"Task {i}", "generate")

        # After 5 points, smoothness/convergence should differ from 0.5
        last_phi = point.metadata["phi_score"]
        # The phi_score should be different from hardcoded (using real values)
        assert last_phi != pytest.approx(hardcoded_phi, abs=0.01)

    def test_consistent_tasks_produce_high_smoothness(self):
        """Consistent tasks (stable spin) produce smoothness > 0.7."""
        tracker = JourneyTracker(seed=42)

        for _i in range(6):
            result = ExecutionResult(
                success=True,
                output="output",
                metrics={"coherence": 0.85},
                duration_seconds=1.0,
                token_metrics={"cache_hit_rate": 0.7},
            )
            tracker.track_execution(result, "Same task", "generate")

        quality = tracker.compute_trajectory_quality(tracker._recent_points)
        assert quality["smoothness"] > 0.7

    def test_divergent_tasks_produce_lower_smoothness_than_consistent(self):
        """Divergent tasks produce lower smoothness than consistent tasks."""
        # Run consistent tasks
        consistent_tracker = JourneyTracker(seed=42)
        for _ in range(5):
            result = ExecutionResult(
                success=True,
                output="output",
                metrics={"coherence": 0.5},
                duration_seconds=1.0,
                token_metrics={"cache_hit_rate": 0.7},
            )
            consistent_tracker.track_execution(result, "Same task", "generate")

        consistent_quality = consistent_tracker.compute_trajectory_quality(
            consistent_tracker._recent_points
        )

        # Run divergent tasks
        divergent_tracker = JourneyTracker(seed=42)
        ops = ["generate", "analyze", "search", "transform", "persist"]
        for i in range(5):
            result = ExecutionResult(
                success=i % 2 == 0,
                output="output",
                metrics={"coherence": 0.2 + 0.15 * i},
                duration_seconds=1.0 + i,
                token_metrics={"cache_hit_rate": 0.1 * i},
            )
            divergent_tracker.track_execution(result, f"Very different task {i * 100}", ops[i])

        divergent_quality = divergent_tracker.compute_trajectory_quality(
            divergent_tracker._recent_points
        )

        # Divergent tasks should have strictly lower smoothness
        assert divergent_quality["smoothness"] < consistent_quality["smoothness"]

    def test_stable_coherence_produces_high_convergence(self):
        """Stable cohesion values produce convergence > 0.7."""
        tracker = JourneyTracker(seed=42)

        for _i in range(5):
            result = ExecutionResult(
                success=True,
                output="output",
                metrics={"coherence": 0.5},  # Perfect HIHO
                duration_seconds=1.0,
                token_metrics={"cache_hit_rate": 0.7},
            )
            tracker.track_execution(result, "Stable task", "generate")

        quality = tracker.compute_trajectory_quality(tracker._recent_points)
        assert quality["convergence"] > 0.7

    def test_buffer_caps_at_window_size(self):
        """Buffer caps at TRAJECTORY_WINDOW (20 max)."""
        tracker = JourneyTracker(seed=42)

        for i in range(25):
            result = ExecutionResult(
                success=True,
                output="output",
                metrics={"coherence": 0.85},
                duration_seconds=1.0,
                token_metrics={"cache_hit_rate": 0.7},
            )
            tracker.track_execution(result, f"Task {i}", "generate")

        assert len(tracker._recent_points) == tracker.TRAJECTORY_WINDOW


class TestSurrealInjectionSanitization:
    """Review LOW #1: operation_type must be quote-stripped like the sibling task field."""

    def test_operation_type_single_quote_is_sanitized(self):
        """An operation_type containing a single quote must not survive into the SurrealQL literal."""
        import urllib.request
        from unittest.mock import patch

        tracker = JourneyTracker(seed=42)
        point = TrajectoryPoint(
            dimensions=np.array([0.5] * 12),
            timestamp=1.0,
            coherence=0.8,
            efficiency=0.7,
            operation_type="generate'; DROP TABLE journey_transition; --",
            task_description="benign task",
        )

        captured = {}

        def fake_urlopen(req, timeout=None):
            captured["data"] = req.data.decode()
            raise RuntimeError("stop after capture")

        with patch.object(urllib.request, "urlopen", side_effect=fake_urlopen):
            tracker._persist_to_surreal(point)

        query = captured["data"]
        # The single quote from operation_type must be stripped — no stray quote can break the literal.
        assert "DROP TABLE" in query  # the text content is preserved (just de-quoted)
        assert "generate'" not in query  # the quote that would close the literal is gone
        assert "operation_type = 'generate" in query
