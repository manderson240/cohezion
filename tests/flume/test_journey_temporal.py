"""Tests for TemporalEncoder integration in JourneyTracker."""

from __future__ import annotations

import numpy as np
import pytest


try:
    import torch  # noqa: F401

    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

pytestmark = pytest.mark.skipif(not TORCH_AVAILABLE, reason="PyTorch not installed")


def _make_step(seed: int = 0) -> dict:
    rng = np.random.RandomState(seed)
    traj = rng.randn(12).tolist()
    return {
        "trajectory": traj,
        "coherence": 0.6,
        "novelty": 0.5,
        "improvement": 1.0,
        "skill": "analyze",
    }


class TestJourneyTrackerTemporalEncoder:
    """TemporalEncoder path in JourneyTracker."""

    def test_encode_step_sequence_returns_2048d(self) -> None:
        """encode_step_sequence() returns 2048D array."""
        from cohezion.compound.journey_tracker import JourneyTracker

        tracker = JourneyTracker()
        steps = [_make_step(i) for i in range(5)]
        result = tracker.encode_step_sequence(steps)

        assert isinstance(result, np.ndarray)
        assert result.shape == (2048,)
        assert result.dtype == np.float32 or result.dtype == np.float64

    def test_encode_step_sequence_normalized(self) -> None:
        """Output is normalized to [-1, 1]."""
        from cohezion.compound.journey_tracker import JourneyTracker

        tracker = JourneyTracker()
        steps = [_make_step(i) for i in range(8)]
        result = tracker.encode_step_sequence(steps)

        assert result.min() >= -1.0 - 1e-5
        assert result.max() <= 1.0 + 1e-5

    def test_encode_step_sequence_deterministic(self) -> None:
        """Same steps produce the same encoding (temporal encoder in eval mode)."""
        from cohezion.compound.journey_tracker import JourneyTracker

        tracker = JourneyTracker()
        steps = [_make_step(i) for i in range(5)]
        result1 = tracker.encode_step_sequence(steps)
        result2 = tracker.encode_step_sequence(steps)

        np.testing.assert_array_almost_equal(result1, result2, decimal=5)

    def test_encode_step_sequence_single_step(self) -> None:
        """Works with a single step."""
        from cohezion.compound.journey_tracker import JourneyTracker

        tracker = JourneyTracker()
        result = tracker.encode_step_sequence([_make_step(0)])
        assert result.shape == (2048,)

    def test_encode_step_sequence_different_steps(self) -> None:
        """Different step sequences produce different encodings."""
        from cohezion.compound.journey_tracker import JourneyTracker

        tracker = JourneyTracker()
        steps_a = [_make_step(i) for i in range(5)]
        steps_b = [_make_step(i + 100) for i in range(5)]
        result_a = tracker.encode_step_sequence(steps_a)
        result_b = tracker.encode_step_sequence(steps_b)

        assert not np.allclose(result_a, result_b)

    def test_temporal_encoder_is_loaded(self) -> None:
        """JourneyTracker exposes _temporal_encoder attribute."""
        from cohezion.compound.journey_tracker import JourneyTracker

        tracker = JourneyTracker()
        # Attribute must exist (may be None if no checkpoint, but must be declared)
        assert hasattr(tracker, "_temporal_encoder")
