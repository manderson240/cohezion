"""Tests for FLUME VAE training pipeline.

Validates training convergence, checkpoint save/load, latent space
interpolation smoothness, dataset generation, and reconstruction quality.
"""

from __future__ import annotations

import numpy as np
import pytest
import torch

from cohezion.flume.dataset import SyntheticFlumeDataset
from cohezion.flume.training import FlumeVAETrainer, TrainConfig


@pytest.fixture()
def small_config(tmp_path):
    """TrainConfig with small z_dim for fast tests."""
    return TrainConfig(
        z_dim=64,
        batch_size=32,
        epochs=5,
        lr=1e-3,
        checkpoint_dir=str(tmp_path),
        log_interval=1,
    )


@pytest.fixture()
def small_dataset():
    """Small synthetic dataset for fast tests."""
    return SyntheticFlumeDataset(n_samples=500, z_dim=64, seed=42)


class TestTrainingConvergence:
    """Test that VAE training reduces loss over epochs."""

    def test_training_convergence(self, small_config, small_dataset):
        """Loss should decrease over 5 epochs of training."""
        trainer = FlumeVAETrainer(small_config)
        metrics = trainer.train(dataset=small_dataset)

        assert len(metrics) == 5
        assert metrics[-1]["mse"] < metrics[0]["mse"], (
            f"MSE should decrease: first={metrics[0]['mse']:.4f}, last={metrics[-1]['mse']:.4f}"
        )
        assert metrics[-1]["total"] < metrics[0]["total"], (
            f"Total loss should decrease: first={metrics[0]['total']:.4f}, "
            f"last={metrics[-1]['total']:.4f}"
        )


class TestCheckpoints:
    """Test checkpoint save and load."""

    def test_checkpoint_save_load(self, small_config, small_dataset, tmp_path):
        """Checkpoint should contain all model components."""
        trainer = FlumeVAETrainer(small_config)

        # Override to save checkpoint at epoch 5 (config.epochs == 5)
        trainer.train(dataset=small_dataset)

        checkpoint_files = list(tmp_path.glob("flume_vae_ep*.pt"))
        assert len(checkpoint_files) > 0, "No checkpoint files were saved"

        ckpt = torch.load(checkpoint_files[0], weights_only=False)
        expected_keys = {
            "encoder",
            "mu_head",
            "logvar_head",
            "decoder",
            "optimizer",
            "config",
            "epoch",
        }
        assert expected_keys.issubset(ckpt.keys()), (
            f"Missing keys: {expected_keys - set(ckpt.keys())}"
        )


class TestLatentInterpolation:
    """Test that latent space interpolation is smooth."""

    def test_latent_interpolation(self, small_config, small_dataset):
        """Interpolated latent points should decode smoothly."""
        trainer = FlumeVAETrainer(small_config)
        trainer.train(dataset=small_dataset)

        # Create two random input points
        torch.manual_seed(0)
        x1 = torch.randn(1, 64)
        x2 = torch.randn(1, 64)

        # Encode both to get mu vectors
        with torch.no_grad():
            _, mu1, _ = trainer._forward(x1)
            _, mu2, _ = trainer._forward(x2)

        # Interpolate and decode
        alphas = [0.0, 0.25, 0.5, 0.75, 1.0]
        decoded = []
        for alpha in alphas:
            z_interp = alpha * mu1 + (1 - alpha) * mu2
            with torch.no_grad():
                recon = trainer.decoder(z_interp)
            decoded.append(recon.squeeze(0).numpy())

        # Outputs should be different (not collapsed)
        for i in range(len(decoded) - 1):
            diff = np.linalg.norm(decoded[i] - decoded[i + 1])
            assert diff > 0, f"Decoded points {i} and {i + 1} are identical (collapsed)"

        # Consecutive differences should be relatively smooth
        diffs = [np.linalg.norm(decoded[i] - decoded[i + 1]) for i in range(len(decoded) - 1)]
        max_diff = max(diffs)
        min_diff = min(diffs)
        # The ratio of max to min step size should not be extreme
        if min_diff > 0:
            ratio = max_diff / min_diff
            assert ratio < 10.0, f"Interpolation is not smooth: max/min step ratio = {ratio:.2f}"


class TestSyntheticDataset:
    """Test synthetic dataset generation."""

    def test_synthetic_dataset(self):
        """Synthetic dataset should have correct shape and distribution."""
        ds = SyntheticFlumeDataset(n_samples=100, z_dim=32, seed=42)

        assert len(ds) == 100

        item = ds[0]
        assert item.shape == (32,)
        assert item.dtype == torch.float32

        # Check distribution is approximately centered at 0.5
        all_data = torch.stack([ds[i] for i in range(len(ds))])
        mean = all_data.mean().item()
        assert abs(mean - 0.5) < 0.1, f"Dataset mean should be ~0.5, got {mean:.4f}"


class TestReconstructionQuality:
    """Test reconstruction quality after training."""

    def test_reconstruction_quality(self, tmp_path):
        """Reconstruction MSE should be below 0.5 after 10 epochs."""
        config = TrainConfig(
            z_dim=64,
            batch_size=32,
            epochs=10,
            lr=1e-3,
            checkpoint_dir=str(tmp_path),
            log_interval=5,
        )
        dataset = SyntheticFlumeDataset(n_samples=500, z_dim=64, seed=42)
        trainer = FlumeVAETrainer(config)
        trainer.train(dataset=dataset)

        # Take a batch and measure reconstruction error
        batch = torch.stack([dataset[i] for i in range(32)])
        with torch.no_grad():
            recon, _, _ = trainer._forward(batch)
        mse = torch.nn.functional.mse_loss(recon, batch).item()

        assert mse < 0.5, f"Reconstruction MSE too high: {mse:.4f}"
