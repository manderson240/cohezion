"""Tests for VAE training on real experience data (Phase 5).

Validates ExperienceDataset -> FlumeVAETrainer pipeline.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import torch

from cohezion.flume.experience_dataset import ExperienceDataset
from cohezion.flume.experience_encoder import TOTAL_DIM, ExperienceEncoder
from cohezion.flume.training import FlumeVAETrainer, TrainConfig


if TYPE_CHECKING:
    from pathlib import Path


def _make_experience(**overrides) -> dict:
    """Create a minimal valid experience dict."""
    base = {
        "trajectory": np.random.default_rng(42).normal(0.5, 0.15, 12).astype(np.float32),
        "mission_id": "test-mission",
        "agent_id": "test-agent",
        "skill_name": "research",
        "input_preview": "test input",
        "operation_type": "generate",
        "phi_score": 0.85,
        "trajectory_smoothness": 0.75,
        "trajectory_convergence": 0.8,
    }
    base.update(overrides)
    return base


class TestVAEExperienceTraining:
    """Tests for training VAE on real experience data (Phase 5)."""

    def test_experience_dataset_produces_256d_tensors(self):
        """ExperienceDataset produces 256D tensors from mock collector output."""
        experiences = [_make_experience(mission_id=f"m{i}") for i in range(10)]
        ds = ExperienceDataset(experiences, seed=42)

        assert len(ds) == 10
        sample = ds[0]
        assert isinstance(sample, torch.Tensor)
        assert sample.shape == (TOTAL_DIM,)
        assert sample.dtype == torch.float32

    def test_empty_collector_returns_synthetic_fallback(self, tmp_path: Path):
        """Empty collector triggers synthetic fallback in train_from_experiences."""
        from cohezion.flume.experience_collector import ExperienceCollector

        collector = ExperienceCollector(
            parquet_dir=tmp_path / "empty1",
            vault_dir=tmp_path / "empty2",
        )

        config = TrainConfig(epochs=1, batch_size=32, checkpoint_dir=str(tmp_path / "ckpt"))
        trainer = FlumeVAETrainer(config)
        metrics = trainer.train_from_experiences(collector=collector, min_real_samples=5)

        assert len(metrics) == 1  # 1 epoch
        assert "total" in metrics[0]

    def test_train_from_experiences_completes_one_epoch(self, tmp_path: Path):
        """train_from_experiences() completes 1 epoch without error."""
        from cohezion.flume.experience_collector import ExperienceCollector

        # Create a collector with mock data via direct dataset
        config = TrainConfig(epochs=1, batch_size=16, checkpoint_dir=str(tmp_path / "ckpt"))
        trainer = FlumeVAETrainer(config)

        # Train with synthetic fallback (no real data)
        collector = ExperienceCollector(parquet_dir=tmp_path / "np", vault_dir=tmp_path / "nv")
        metrics = trainer.train_from_experiences(collector=collector, min_real_samples=1)

        assert len(metrics) == 1
        assert metrics[0]["total"] > 0

    def test_trained_vae_lower_mse_than_untrained(self):
        """Trained VAE has lower reconstruction MSE than untrained."""
        experiences = [_make_experience(mission_id=f"m{i}", phi_score=0.5 + 0.01 * i) for i in range(200)]
        ds = ExperienceDataset(experiences, seed=42)

        # Measure MSE before training
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            config = TrainConfig(epochs=5, batch_size=32, checkpoint_dir=tmpdir)
            trainer = FlumeVAETrainer(config)

            # Get pre-training MSE
            sample = ds[0].unsqueeze(0)
            with torch.no_grad():
                recon_before, _, _ = trainer._forward(sample)
                mse_before = torch.nn.functional.mse_loss(recon_before, sample).item()

            # Train
            trainer.train(dataset=ds)

            # Get post-training MSE
            with torch.no_grad():
                recon_after, _, _ = trainer._forward(sample)
                mse_after = torch.nn.functional.mse_loss(recon_after, sample).item()

            # Trained VAE should have lower MSE (learned structure)
            assert mse_after < mse_before

    def test_same_experience_produces_same_encoding(self):
        """Same experience dict always produces same 256D encoding (deterministic)."""
        encoder = ExperienceEncoder()
        exp = _make_experience()

        vec1 = encoder.encode(exp)
        vec2 = encoder.encode(exp)

        np.testing.assert_array_equal(vec1, vec2)
