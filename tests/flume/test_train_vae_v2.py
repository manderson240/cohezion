"""Tests for FLUME VAE v2 training pipeline."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import torch


class TestKLAnnealing:
    """Test KL annealing schedule."""

    def test_beta_starts_at_zero(self):
        """Beta should start at 0 at step 0."""
        from cohezion.flume.train_vae import kl_annealing_beta

        assert kl_annealing_beta(step=0, warmup_steps=100, max_beta=0.1) == 0.0

    def test_beta_reaches_max_after_warmup(self):
        """Beta should reach max_beta at warmup_steps."""
        from cohezion.flume.train_vae import kl_annealing_beta

        beta = kl_annealing_beta(step=100, warmup_steps=100, max_beta=0.1)
        assert abs(beta - 0.1) < 1e-6

    def test_beta_stays_at_max_after_warmup(self):
        """Beta should not exceed max_beta after warmup."""
        from cohezion.flume.train_vae import kl_annealing_beta

        beta = kl_annealing_beta(step=200, warmup_steps=100, max_beta=0.1)
        assert abs(beta - 0.1) < 1e-6

    def test_beta_linearly_increases(self):
        """Beta should increase linearly during warmup."""
        from cohezion.flume.train_vae import kl_annealing_beta

        beta_half = kl_annealing_beta(step=50, warmup_steps=100, max_beta=0.1)
        assert abs(beta_half - 0.05) < 1e-6


class TestActiveUnits:
    """Test active unit counting."""

    def test_counts_active_units(self):
        """Should count dimensions with variance above threshold."""
        from cohezion.flume.train_vae import count_active_units

        # 128 dims with high variance, 128 with low
        mu = torch.randn(100, 256)
        mu[:, 128:] = 0.0  # Kill variance in last 128 dims

        active = count_active_units(mu, threshold=0.01)
        # First 128 should be active (randn has var ~1)
        assert active >= 100  # At least 100 of 128 should be active

    def test_all_active_when_varied(self):
        """All units should be active when all dimensions vary."""
        from cohezion.flume.train_vae import count_active_units

        mu = torch.randn(200, 256)
        active = count_active_units(mu, threshold=0.01)
        assert active >= 240  # Almost all should be active


class TestVAETrainer:
    """Test the training loop."""

    def test_loss_decreases_over_epochs(self):
        """Loss should decrease after a few training epochs on synthetic data."""
        from cohezion.flume.train_vae import VAETrainer
        from cohezion.flume.vae import FlumeVAE

        torch.manual_seed(42)
        model = FlumeVAE(input_dim=768, latent_dim=256)
        data = torch.randn(200, 768)

        trainer = VAETrainer(model, lr=1e-3, max_beta=0.1, warmup_fraction=0.3)
        history = trainer.train(data, epochs=5, batch_size=32)

        assert history[-1]["total_loss"] < history[0]["total_loss"]

    def test_checkpoint_save_and_load(self, tmp_path: Path):
        """Checkpoint should save and load correctly."""
        from cohezion.flume.train_vae import VAETrainer
        from cohezion.flume.vae import FlumeVAE

        torch.manual_seed(42)
        model = FlumeVAE(input_dim=768, latent_dim=256)
        trainer = VAETrainer(model, lr=1e-3)

        ckpt_path = tmp_path / "test_checkpoint.pt"
        trainer.save_checkpoint(ckpt_path, epoch=5, metrics={"loss": 0.5})

        assert ckpt_path.exists()

        # Load into new model
        model2 = FlumeVAE(input_dim=768, latent_dim=256)
        trainer2 = VAETrainer(model2, lr=1e-3)
        loaded = trainer2.load_checkpoint(ckpt_path)

        assert loaded["epoch"] == 5
        assert loaded["metrics"]["loss"] == 0.5

        # Verify models produce same output
        x = torch.randn(2, 768)
        model.eval()
        model2.eval()
        with torch.no_grad():
            out1 = model(x)
            out2 = model2(x)
        torch.testing.assert_close(out1[0], out2[0])

    def test_training_records_kl_and_recon(self):
        """Training history should record KL and reconstruction losses."""
        from cohezion.flume.train_vae import VAETrainer
        from cohezion.flume.vae import FlumeVAE

        torch.manual_seed(42)
        model = FlumeVAE(input_dim=768, latent_dim=256)
        data = torch.randn(100, 768)

        trainer = VAETrainer(model, lr=1e-3)
        history = trainer.train(data, epochs=2, batch_size=32)

        for entry in history:
            assert "total_loss" in entry
            assert "recon_loss" in entry
            assert "kl_loss" in entry
            assert "beta" in entry

    def test_grad_clipping_applied(self):
        """Gradient clipping should prevent explosion."""
        from cohezion.flume.train_vae import VAETrainer
        from cohezion.flume.vae import FlumeVAE

        model = FlumeVAE(input_dim=768, latent_dim=256)
        trainer = VAETrainer(model, lr=1e-3, grad_clip=1.0)

        # Train one step with large input to trigger large gradients
        data = torch.randn(32, 768) * 100
        history = trainer.train(data, epochs=1, batch_size=32)

        # Should complete without NaN
        assert not any(np.isnan(h["total_loss"]) for h in history)
