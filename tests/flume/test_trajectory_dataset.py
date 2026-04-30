"""Tests for TrajectorySequenceDataset — groups journey records into step sequences."""

from __future__ import annotations

import json

import numpy as np
import pytest
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


try:
    import torch

    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

pytestmark = pytest.mark.skipif(not TORCH_AVAILABLE, reason="PyTorch not installed")

STEP_DIM = 29


def _make_journey_records(n_sessions: int, steps_per_session: int, seed: int = 0) -> list[dict]:
    """Create synthetic journey records mimicking data/overnight/journeys.jsonl."""
    rng = np.random.RandomState(seed)
    records = []
    op_types = ["generate", "analyze", "search", "transform", "persist"]
    for session in range(n_sessions):
        session_id = f"session_{session:04d}"
        for step in range(steps_per_session):
            trajectory = rng.randn(12).astype(float).tolist()
            norm = float(np.linalg.norm(trajectory)) or 1.0
            trajectory = [v / norm for v in trajectory]
            records.append(
                {
                    "id": f"{session:04d}_{step:04d}",
                    "session_id": session_id,
                    "iteration": step,
                    "skill": op_types[step % len(op_types)],
                    "coherence": float(rng.uniform(0.5, 0.75)),
                    "novelty": 0.5,
                    "improvement": 1.0,
                    "trajectory": trajectory,
                }
            )
    return records


@pytest.fixture
def jsonl_file(tmp_path: Path) -> Path:
    """Write synthetic journey records to a JSONL file."""
    records = _make_journey_records(n_sessions=5, steps_per_session=20)
    path = tmp_path / "journeys.jsonl"
    with open(path, "w") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")
    return path


class TestTrajectorySequenceDataset:
    """Test dataset groups records into sequences."""

    def test_dataset_length(self, jsonl_file: Path) -> None:
        """Dataset length equals number of sessions."""
        from cohezion.flume.trajectory_dataset import TrajectorySequenceDataset

        ds = TrajectorySequenceDataset(jsonl_file, max_seq_len=20)
        assert len(ds) == 5  # 5 sessions

    def test_item_shape(self, jsonl_file: Path) -> None:
        """Each item is a tensor [seq_len, STEP_DIM]."""
        from cohezion.flume.trajectory_dataset import TrajectorySequenceDataset

        ds = TrajectorySequenceDataset(jsonl_file, max_seq_len=20)
        item = ds[0]
        assert isinstance(item, torch.Tensor)
        assert item.shape[1] == STEP_DIM
        assert item.dtype == torch.float32

    def test_step_dim_layout(self, jsonl_file: Path) -> None:
        """First 12 dims are trajectory, next 12 metrics, last 5 op_type one-hot."""
        from cohezion.flume.trajectory_dataset import TrajectorySequenceDataset

        ds = TrajectorySequenceDataset(jsonl_file, max_seq_len=20)
        item = ds[0]  # [T, 29]
        # op_type dims [24:29] should sum to 1.0 (one-hot) for each step
        op_one_hot = item[:, 24:29]
        sums = op_one_hot.sum(dim=1)
        assert torch.allclose(sums, torch.ones(len(sums)), atol=1e-5)

    def test_max_seq_len_truncation(self, tmp_path: Path) -> None:
        """Sequences longer than max_seq_len are truncated."""
        from cohezion.flume.trajectory_dataset import TrajectorySequenceDataset

        records = _make_journey_records(n_sessions=2, steps_per_session=50)
        path = tmp_path / "long.jsonl"
        with open(path, "w") as f:
            for r in records:
                f.write(json.dumps(r) + "\n")

        ds = TrajectorySequenceDataset(path, max_seq_len=15)
        for i in range(len(ds)):
            assert ds[i].shape[0] <= 15

    def test_collate_fn_pads_to_equal_length(self, tmp_path: Path) -> None:
        """collate_fn pads variable-length sequences in a batch."""
        from cohezion.flume.trajectory_dataset import TrajectorySequenceDataset, collate_sequences

        # Create sessions with different lengths
        rng = np.random.RandomState(0)
        records = []
        for s, length in enumerate([5, 10, 15]):
            for step in range(length):
                traj = rng.randn(12).tolist()
                records.append(
                    {
                        "id": f"s{s}_{step}",
                        "session_id": f"session_{s}",
                        "iteration": step,
                        "skill": "generate",
                        "coherence": 0.55,
                        "novelty": 0.5,
                        "improvement": 1.0,
                        "trajectory": traj,
                    }
                )
        path = tmp_path / "var.jsonl"
        with open(path, "w") as f:
            for r in records:
                f.write(json.dumps(r) + "\n")

        ds = TrajectorySequenceDataset(path, max_seq_len=20)
        batch = collate_sequences([ds[0], ds[1], ds[2]])

        sequences, padding_mask = batch
        assert sequences.shape[0] == 3
        assert sequences.shape[2] == STEP_DIM
        # padding_mask: True = padded, shape [B, T]
        assert padding_mask.shape[:2] == sequences.shape[:2]
        assert padding_mask.dtype == torch.bool

    def test_from_records_list(self) -> None:
        """Can construct dataset from in-memory list of records."""
        from cohezion.flume.trajectory_dataset import TrajectorySequenceDataset

        records = _make_journey_records(n_sessions=3, steps_per_session=8)
        ds = TrajectorySequenceDataset.from_records(records, max_seq_len=10)
        assert len(ds) == 3
        assert ds[0].shape[1] == STEP_DIM
