"""Tests for FLUME domain encoder and trajectory capture."""

from unittest.mock import AsyncMock, patch

import numpy as np

from cohezion.flume.domain_encoder import (
    MANIFOLD_DIM,
    EncodedTrajectoryPoint,
    GenericEncoder,
    InteractiveGameEncoder,
    KernelOptimizationEncoder,
    MathProblemEncoder,
    get_encoder,
)
from cohezion.flume.trajectory_capture import capture_trajectory


class TestEncodedTrajectoryPoint:
    def test_serialization_roundtrip(self):
        pt = EncodedTrajectoryPoint(
            domain="aimo",
            state_12d=np.ones(12, dtype=np.float32),
            action_description="solve",
            reward=1.0,
            surprise=0.05,
        )
        d = pt.to_dict()
        assert isinstance(d["state_12d"], list)
        assert len(d["state_12d"]) == 12

        restored = EncodedTrajectoryPoint.from_dict(d)
        assert restored.domain == "aimo"
        assert restored.reward == 1.0
        assert restored.surprise == 0.05
        np.testing.assert_array_almost_equal(restored.state_12d, pt.state_12d)

    def test_default_metadata(self):
        pt = EncodedTrajectoryPoint(
            domain="test",
            state_12d=np.zeros(12, dtype=np.float32),
            action_description="noop",
            reward=0.0,
        )
        assert pt.surprise is None
        assert pt.metadata == {}


class TestMathProblemEncoder:
    def test_produces_12d(self):
        enc = MathProblemEncoder()
        state = {"difficulty": 7, "confidence": 0.9, "correctness": 1.0}
        vec = enc.encode(state)
        assert vec.shape == (MANIFOLD_DIM,)
        assert vec.dtype == np.float32

    def test_domain_name(self):
        assert MathProblemEncoder().domain_name() == "aimo"

    def test_values_in_range(self):
        enc = MathProblemEncoder()
        state = {
            "problem_length": 500,
            "difficulty": 10,
            "topic": "algebra",
            "step_count": 20,
            "confidence": 1.0,
            "verification_status": True,
            "time_spent": 3600,
            "tokens_used": 100000,
            "attempt_number": 5,
            "coherence": 0.8,
            "novelty": 0.5,
            "correctness": 1.0,
        }
        vec = enc.encode(state)
        assert np.all(vec >= -1.0)
        assert np.all(vec <= 1.0)


class TestKernelOptimizationEncoder:
    def test_produces_12d(self):
        enc = KernelOptimizationEncoder()
        state = {"geomean_us": 42.5, "test_pass_rate": 0.95}
        vec = enc.encode(state)
        assert vec.shape == (MANIFOLD_DIM,)
        assert vec.dtype == np.float32

    def test_domain_name(self):
        assert KernelOptimizationEncoder().domain_name() == "luma-gemm"


class TestInteractiveGameEncoder:
    def test_produces_12d(self):
        enc = InteractiveGameEncoder()
        state = {"grid_entropy": 0.7, "goal_proximity": 0.3}
        vec = enc.encode(state)
        assert vec.shape == (MANIFOLD_DIM,)
        assert vec.dtype == np.float32

    def test_domain_name(self):
        assert InteractiveGameEncoder().domain_name() == "arc-agi"


class TestGenericEncoder:
    def test_produces_12d_from_arbitrary_dict(self):
        enc = GenericEncoder(domain="nemotron")
        state = {"foo": 42, "bar": "baz", "nested": [1, 2, 3]}
        vec = enc.encode(state)
        assert vec.shape == (MANIFOLD_DIM,)
        assert vec.dtype == np.float32

    def test_deterministic(self):
        enc = GenericEncoder()
        state = {"x": 1, "y": 2}
        v1 = enc.encode(state)
        v2 = enc.encode(state)
        np.testing.assert_array_equal(v1, v2)

    def test_different_inputs_produce_different_vectors(self):
        enc = GenericEncoder()
        v1 = enc.encode({"a": 1})
        v2 = enc.encode({"b": 2})
        assert not np.allclose(v1, v2)


class TestGetEncoder:
    def test_returns_math_encoder(self):
        enc = get_encoder("aimo")
        assert isinstance(enc, MathProblemEncoder)

    def test_returns_kernel_encoder(self):
        enc = get_encoder("luma-gemm")
        assert isinstance(enc, KernelOptimizationEncoder)

    def test_returns_game_encoder(self):
        enc = get_encoder("arc-agi")
        assert isinstance(enc, InteractiveGameEncoder)

    def test_unknown_domain_returns_generic(self):
        enc = get_encoder("some-new-competition")
        assert isinstance(enc, GenericEncoder)
        assert enc.domain_name() == "some-new-competition"


class TestCaptureTrajectory:
    def test_records_points(self):
        with capture_trajectory("aimo", agent_id="test") as cap:
            cap.record(state={"difficulty": 5}, action="solve", reward=1.0)
            cap.record(state={"difficulty": 8}, action="verify", reward=0.5)

        assert len(cap.points) == 2
        assert cap.points[0].domain == "aimo"
        assert cap.points[1].action_description == "verify"

    @patch("cohezion.flume.trajectory_capture._async_persist", new_callable=AsyncMock)
    def test_persist_called_on_exit(self, mock_persist):
        with capture_trajectory("arc-agi") as cap:
            cap.record(state={"grid_entropy": 0.5}, action="interact", reward=0.0)
        # Persistence is best-effort; mock should have been called
        mock_persist.assert_called_once()
