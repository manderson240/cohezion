"""Tests for trajectory statistics computation (Phase 2).

Validates that ExperienceCollector preserves full trajectory dynamics
and ExperienceEncoder maps trajectory_smoothness/trajectory_convergence
into the 256D vector.
"""

from __future__ import annotations

import numpy as np

from cohezion.flume.experience_collector import ExperienceCollector
from cohezion.flume.experience_encoder import TOTAL_DIM, ExperienceEncoder


class TestTrajectoryStats:
    """Tests for trajectory_smoothness and trajectory_convergence computation."""

    def test_multi_point_trajectory_produces_nonzero_stats(self):
        """Multi-point trajectory produces non-zero smoothness/convergence."""
        # 5 slowly-drifting 12D points across fabrics
        traj = [np.full(12, 0.5 + 0.01 * i, dtype=np.float32) for i in range(5)]
        row = {"state_trajectory": traj, "mission_id": "m1"}
        result = ExperienceCollector._normalize_parquet_row(row)

        assert result["trajectory_smoothness"] > 0.0
        assert result["trajectory_smoothness"] <= 1.0
        assert result["trajectory_convergence"] > 0.0
        assert result["trajectory_convergence"] <= 1.0

    def test_single_point_trajectory_defaults_gracefully(self):
        """Single-point trajectory defaults to smoothness=1.0 (no breaking observed)."""
        traj = [np.full(12, 0.5, dtype=np.float32)]
        row = {"state_trajectory": traj}
        result = ExperienceCollector._normalize_parquet_row(row)

        assert result["trajectory_smoothness"] == 1.0
        assert result["trajectory_convergence"] == 1.0

    def test_encoded_vector_has_nonzero_trajectory_slots(self):
        """Encoded 256D vector has non-zero trajectory metric slots."""
        encoder = ExperienceEncoder()
        exp = {
            "trajectory": np.full(12, 0.5, dtype=np.float32),
            "operation_type": "generate",
            "trajectory_smoothness": 0.85,
            "trajectory_convergence": 0.72,
        }
        vec = encoder.encode(exp)

        assert vec.shape == (TOTAL_DIM,)
        # trajectory_smoothness is at METRIC_KEYS index 9, trajectory_convergence at 10
        # dims 12+9=21, 12+10=22
        assert vec[21] > 0.0  # trajectory_smoothness
        assert vec[22] > 0.0  # trajectory_convergence

    def test_empty_trajectory_produces_valid_vector(self):
        """Empty trajectory still produces valid 256D vector (backward compat)."""
        encoder = ExperienceEncoder()
        exp = {
            "trajectory": np.zeros(12, dtype=np.float32),
            "operation_type": "analyze",
        }
        vec = encoder.encode(exp)

        assert vec.shape == (TOTAL_DIM,)
        assert np.isfinite(vec).all()

    def test_surreal_rows_compute_trajectory_stats(self):
        """SurrealDB rows also compute trajectory stats from state_trajectory."""
        traj = [np.full(12, 0.5 + 0.02 * i, dtype=np.float32) for i in range(4)]
        row = {"state_trajectory": traj, "id": "surreal:1"}
        result = ExperienceCollector._normalize_surreal_row(row)

        assert "trajectory_smoothness" in result
        assert "trajectory_convergence" in result
        assert result["trajectory_smoothness"] > 0.0
        assert result["trajectory_convergence"] > 0.0
