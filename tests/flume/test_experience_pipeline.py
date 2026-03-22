"""Tests for the Experience -> VAE Training Pipeline.

5 focused tests covering encoder, dataset, collector, and end-to-end pipeline.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import torch

from cohezion.flume.experience_encoder import (
    OPERATION_TYPES,
    TOTAL_DIM,
    ExperienceEncoder,
)


if TYPE_CHECKING:
    from pathlib import Path


def _make_experience(**overrides: object) -> dict:
    """Create a minimal valid experience dict."""
    base: dict = {
        "trajectory": np.random.default_rng(42).normal(0.5, 0.15, 12).astype(np.float32),
        "mission_id": "test-mission-1",
        "agent_id": "test-agent",
        "skill_name": "research",
        "input_preview": "test input",
        "operation_type": "generate",
        "phi_score": 0.85,
    }
    base.update(overrides)
    return base


class TestExperienceEncoder:
    """Test ExperienceEncoder output shape, determinism, and one-hot encoding."""

    def test_encoder_output_shape_and_determinism(self) -> None:
        """Encode same experience twice -> identical 256D vectors."""
        encoder = ExperienceEncoder()
        exp = _make_experience()

        vec1 = encoder.encode(exp)
        vec2 = encoder.encode(exp)

        assert vec1.shape == (TOTAL_DIM,)
        assert vec1.dtype == np.float32
        np.testing.assert_array_equal(vec1, vec2)

    def test_encoder_operation_type_onehot(self) -> None:
        """Each operation type activates exactly the correct dimension."""
        encoder = ExperienceEncoder()

        for i, op in enumerate(OPERATION_TYPES):
            exp = _make_experience(operation_type=op)
            vec = encoder.encode(exp)

            # One-hot region is dims [24:29]
            onehot = vec[24:29]
            assert onehot[i] == 1.0, f"Expected dim {i} active for {op}"
            # All others should be 0
            for j in range(len(OPERATION_TYPES)):
                if j != i:
                    assert onehot[j] == 0.0, f"Expected dim {j} inactive for {op}"


class TestExperienceDataset:
    """Test ExperienceDataset returns correct tensors."""

    def test_dataset_returns_correct_tensor(self) -> None:
        """dataset[0] is a torch.Tensor of shape (256,)."""
        from cohezion.flume.experience_dataset import ExperienceDataset

        experiences = [_make_experience(mission_id=f"m{i}") for i in range(5)]
        ds = ExperienceDataset(experiences, seed=42)

        assert len(ds) == 5
        sample = ds[0]
        assert isinstance(sample, torch.Tensor)
        assert sample.shape == (TOTAL_DIM,)
        assert sample.dtype == torch.float32


class TestExperienceCollector:
    """Test ExperienceCollector handles missing directories gracefully."""

    def test_collector_handles_missing_dirs(self, tmp_path: Path) -> None:
        """Empty/missing parquet and vault dirs -> empty list, no crash."""
        from unittest.mock import patch

        from cohezion.flume.experience_collector import ExperienceCollector

        collector = ExperienceCollector(
            parquet_dir=tmp_path / "nonexistent_parquet",
            vault_dir=tmp_path / "nonexistent_vault",
        )
        # Mock the SurrealDB tier to isolate from live data — this test only
        # validates filesystem tier behavior when directories don't exist.
        with patch.object(collector, "_collect_surreal", return_value=[]):
            results = collector.collect_all()
        assert isinstance(results, list)
        assert len(results) == 0


class TestExperiencePipeline:
    """Test end-to-end pipeline with synthetic fallback."""

    def test_pipeline_trains_with_synthetic_fallback(self, tmp_path: Path) -> None:
        """Full pipeline with no real data -> checkpoint saved via synthetic fallback."""
        import asyncio

        from cohezion.flume.experience_collector import ExperienceCollector
        from cohezion.flume.experience_pipeline import ExperienceTrainingPipeline

        checkpoint_dir = tmp_path / "checkpoints"
        collector = ExperienceCollector(
            parquet_dir=tmp_path / "empty_parquet",
            vault_dir=tmp_path / "empty_vault",
        )
        pipeline = ExperienceTrainingPipeline(collector=collector)

        epochs = 2
        checkpoint_path = asyncio.run(
            pipeline.run(
                min_real=1,
                max_samples=200,
                epochs=epochs,
                batch_size=32,
                lr=1e-3,
                seed=42,
                synthetic_fallback=True,
                checkpoint_dir=str(checkpoint_dir),
            )
        )

        # Checkpoint should exist
        assert checkpoint_path.exists(), f"Checkpoint not found at {checkpoint_path}"
        # Verify it's a valid torch checkpoint
        ckpt = torch.load(checkpoint_path, weights_only=False)
        assert "epoch" in ckpt
        assert ckpt["epoch"] == epochs
