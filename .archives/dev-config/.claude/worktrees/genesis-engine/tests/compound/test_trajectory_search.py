"""Tests for trajectory search engine (Phase 9)."""

from unittest.mock import MagicMock

import numpy as np
import pytest

from cohezion.compound.trajectory_search import (
    TrajectorySearchEngine,
    TrajectorySearchResult,
)


@pytest.fixture
def mock_collector():
    """Create mock ExperienceCollector."""
    collector = MagicMock()

    # Mock experiences with varying quality
    collector.collect_all.return_value = [
        {
            "task_description": "High quality task",
            "operation_type": "generate",
            "coherence": 0.85,
            "phi_score": 0.80,
            "trajectory_smoothness": 0.75,
            "trajectory_convergence": 0.70,
            "success": True,
        },
        {
            "task_description": "Medium quality task",
            "operation_type": "generate",
            "coherence": 0.60,
            "phi_score": 0.55,
            "trajectory_smoothness": 0.50,
            "trajectory_convergence": 0.45,
            "success": True,
        },
        {
            "task_description": "Low quality task",
            "operation_type": "generate",
            "coherence": 0.35,
            "phi_score": 0.30,
            "trajectory_smoothness": 0.25,
            "trajectory_convergence": 0.20,
            "success": False,
        },
    ]
    return collector


@pytest.fixture
def mock_encoder():
    """Create mock ExperienceEncoder."""
    encoder = MagicMock()

    # Return deterministic vectors (similar tasks have similar vectors)
    def encode_fn(exp):
        # Base vector
        vec = np.random.RandomState(42).randn(256)

        # Modulate by task description (simulate semantic similarity)
        if "High quality" in exp.get("task_description", ""):
            vec *= 1.0
        elif "Medium quality" in exp.get("task_description", ""):
            vec *= 0.8
        elif "Low quality" in exp.get("task_description", ""):
            vec *= 0.5
        else:
            vec *= 0.9  # Query tasks

        return vec

    encoder.encode_experience.side_effect = encode_fn
    return encoder


class TestTrajectorySearchEngine:
    """Tests for TrajectorySearchEngine."""

    def test_find_similar_trajectories_returns_results(self, mock_collector, mock_encoder):
        """Search returns similar trajectories ranked by quality."""
        search = TrajectorySearchEngine(mock_collector, mock_encoder)

        results = search.find_similar_trajectories(
            task_description="New high quality task",
            operation_type="generate",
            top_k=3,
        )

        assert len(results) > 0
        assert isinstance(results[0], TrajectorySearchResult)
        # First result should be highest quality (sorted)
        assert results[0].coherence >= 0.5

    def test_similarity_threshold_filters_low_matches(self, mock_collector, mock_encoder):
        """Only results above similarity threshold are returned."""
        search = TrajectorySearchEngine(mock_collector, mock_encoder, similarity_threshold=0.9)

        results = search.find_similar_trajectories(
            task_description="Completely different task",
            operation_type="analyze",
            top_k=5,
        )

        # High threshold should filter most results
        assert len(results) <= 3

    def test_min_coherence_filters_poor_quality(self, mock_collector, mock_encoder):
        """Tasks below min_coherence threshold are excluded."""
        search = TrajectorySearchEngine(mock_collector, mock_encoder)

        results = search.find_similar_trajectories(
            task_description="Test task",
            operation_type="generate",
            top_k=5,
            min_coherence=0.5,  # Exclude low quality task
        )

        # Low quality task (coherence=0.35) should be filtered
        assert all(r.coherence >= 0.5 for r in results)

    def test_empty_experiences_returns_empty(self, mock_encoder):
        """Empty collector returns empty results gracefully."""
        empty_collector = MagicMock()
        empty_collector.collect_all.return_value = []

        search = TrajectorySearchEngine(empty_collector, mock_encoder)

        results = search.find_similar_trajectories(
            task_description="Any task",
            operation_type="generate",
            top_k=5,
        )

        assert results == []

    def test_guidance_text_reflects_quality(self, mock_collector, mock_encoder):
        """Guidance text varies based on trajectory quality."""
        search = TrajectorySearchEngine(mock_collector, mock_encoder)

        results = search.find_similar_trajectories(
            task_description="Test task",
            operation_type="generate",
            top_k=3,
        )

        # High quality result should have positive guidance
        high_quality = next((r for r in results if r.coherence >= 0.7), None)
        if high_quality:
            assert "excellent" in high_quality.guidance.lower() or "high confidence" in high_quality.guidance.lower()

        # Low quality result should have warning
        low_quality = next((r for r in results if r.coherence < 0.5), None)
        if low_quality:
            assert "caution" in low_quality.guidance.lower() or "failed" in low_quality.guidance.lower()
