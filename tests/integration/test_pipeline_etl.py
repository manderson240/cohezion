"""Integration tests for the ETL pipeline: sim → export → load → train.

Tests the full data flow from mass simulation output through the
checkpoint exporter to the FlumeTrajectoryDataset.
"""

from __future__ import annotations

import numpy as np
import pytest

from cohezion.flume.dataset import FlumeTrajectoryDataset
from cohezion.mass_sim.config import CheckpointData, UniverseResult
from cohezion.mass_sim.exporter import CheckpointExporter


@pytest.fixture
def tmp_artifact_dir(tmp_path):
    """Temporary directory for test artifacts."""
    d = tmp_path / "artifacts"
    d.mkdir()
    return d


@pytest.fixture
def mock_universe_result() -> UniverseResult:
    """Create a mock UniverseResult with sample states."""
    rng = np.random.default_rng(42)
    checkpoints = []
    for epoch in [100, 200, 300]:
        sample_states = rng.normal(0.5, 0.25, (10, 256)).tolist()
        checkpoints.append(
            CheckpointData(
                epoch=epoch,
                stats={"mean_coherence": 0.5, "pct_within_bounds": 0.9},
                sample_states=sample_states,
            )
        )
    return UniverseResult(
        universe_id="universe_0",
        seed=0,
        n_agents=100,
        n_epochs=300,
        initial_stats={"mean_coherence": 0.05},
        final_stats={"mean_coherence": 0.5, "pct_within_bounds": 0.92},
        checkpoints=checkpoints,
        elapsed_seconds=1.5,
    )


class TestCheckpointExporter:
    """Tests for CheckpointExporter."""

    def test_export_universe_to_npy(self, tmp_artifact_dir, mock_universe_result):
        exporter = CheckpointExporter(tmp_artifact_dir)
        paths = exporter.export_universe_to_npy(mock_universe_result)

        assert len(paths) == 3  # One per checkpoint
        for p in paths:
            assert p.suffix == ".npy"
            arr = np.load(p)
            assert arr.shape == (10, 256)
            assert arr.dtype == np.float32

    def test_export_final_only(self, tmp_artifact_dir, mock_universe_result):
        exporter = CheckpointExporter(tmp_artifact_dir)
        paths = exporter.export_universe_to_npy(mock_universe_result, include_checkpoints=False)

        assert len(paths) == 1
        assert "ep300" in paths[0].name

    def test_export_final_states(self, tmp_artifact_dir):
        exporter = CheckpointExporter(tmp_artifact_dir)
        states = np.random.default_rng(0).normal(0.5, 0.1, (50, 256)).astype(np.float32)

        path = exporter.export_final_states("universe_42", states)
        assert path.exists()
        loaded = np.load(path)
        np.testing.assert_array_equal(loaded, states)

    def test_empty_checkpoints(self, tmp_artifact_dir):
        result = UniverseResult(
            universe_id="empty",
            seed=0,
            n_agents=10,
            n_epochs=100,
            initial_stats={},
            final_stats={},
            checkpoints=[CheckpointData(epoch=100, stats={}, sample_states=None)],
        )
        exporter = CheckpointExporter(tmp_artifact_dir)
        paths = exporter.export_universe_to_npy(result)
        assert len(paths) == 0


class TestETLRoundTrip:
    """Test the full sim → export → load pipeline."""

    def test_export_then_load(self, tmp_artifact_dir, mock_universe_result):
        """Verify exported .npy files can be loaded by FlumeTrajectoryDataset."""
        # Export
        exporter = CheckpointExporter(tmp_artifact_dir)
        exporter.export_universe_to_npy(mock_universe_result)

        # Load
        dataset = FlumeTrajectoryDataset(data_dir=tmp_artifact_dir, max_samples=100)

        # 3 checkpoints x 10 samples = 30
        assert len(dataset) == 30
        sample = dataset[0]
        assert sample.shape == (256,)
        assert sample.dtype.is_floating_point

    def test_export_final_then_load(self, tmp_artifact_dir):
        """Verify final state export can be loaded."""
        rng = np.random.default_rng(0)
        states = rng.normal(0.5, 0.15, (100, 256)).astype(np.float32)

        exporter = CheckpointExporter(tmp_artifact_dir)
        exporter.export_final_states("universe_0", states)

        dataset = FlumeTrajectoryDataset(data_dir=tmp_artifact_dir)
        assert len(dataset) == 100
        assert dataset[0].shape == (256,)

    def test_single_file_loads_correctly(self, tmp_artifact_dir):
        """Verify single .npy file loads correctly."""
        rng = np.random.default_rng(0)
        states = rng.normal(0.5, 0.15, (50, 256)).astype(np.float32)
        np.save(tmp_artifact_dir / "test_final.npy", states)

        dataset = FlumeTrajectoryDataset(data_dir=tmp_artifact_dir)
        assert len(dataset) == 50

    def test_multiple_universes(self, tmp_artifact_dir):
        """Verify data from multiple universes is merged."""
        rng = np.random.default_rng(0)
        for i in range(3):
            states = rng.normal(0.5, 0.15, (20, 256)).astype(np.float32)
            np.save(tmp_artifact_dir / f"universe_{i}_final.npy", states)

        dataset = FlumeTrajectoryDataset(data_dir=tmp_artifact_dir, max_samples=100)
        assert len(dataset) == 60  # 3 x 20
