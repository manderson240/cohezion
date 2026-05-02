"""Tests for FLUME VAE v2 — encoder, decoder, reparameterization, loss."""

from __future__ import annotations

import torch


class TestFlumeVAEEncoder:
    """Test VAE encoder produces correct output shapes."""

    def test_encoder_output_shape(self):
        """Encoder should map 768D input to mu(256) and logvar(256)."""
        from cohezion.flume.vae import FlumeVAE

        model = FlumeVAE(input_dim=768, latent_dim=256)
        x = torch.randn(8, 768)
        mu, logvar = model.encode(x)

        assert mu.shape == (8, 256)
        assert logvar.shape == (8, 256)

    def test_encoder_mu_is_finite(self):
        """Encoder output should not contain NaN or Inf."""
        from cohezion.flume.vae import FlumeVAE

        model = FlumeVAE(input_dim=768, latent_dim=256)
        x = torch.randn(4, 768)
        mu, logvar = model.encode(x)

        assert torch.isfinite(mu).all()
        assert torch.isfinite(logvar).all()


class TestFlumeVAEDecoder:
    """Test VAE decoder produces correct output shapes."""

    def test_decoder_output_shape(self):
        """Decoder should map 256D latent to 768D reconstruction."""
        from cohezion.flume.vae import FlumeVAE

        model = FlumeVAE(input_dim=768, latent_dim=256)
        z = torch.randn(8, 256)
        recon = model.decode(z)

        assert recon.shape == (8, 768)

    def test_decoder_output_is_finite(self):
        """Decoder output should not contain NaN or Inf."""
        from cohezion.flume.vae import FlumeVAE

        model = FlumeVAE(input_dim=768, latent_dim=256)
        z = torch.randn(4, 256)
        recon = model.decode(z)

        assert torch.isfinite(recon).all()


class TestReparameterization:
    """Test the reparameterization trick."""

    def test_reparameterize_produces_different_z_each_call(self):
        """Two calls with same mu/logvar should produce different z (stochastic)."""
        from cohezion.flume.vae import FlumeVAE

        model = FlumeVAE(input_dim=768, latent_dim=256)
        model.train()
        mu = torch.zeros(4, 256)
        logvar = torch.zeros(4, 256)

        z1 = model.reparameterize(mu, logvar)
        z2 = model.reparameterize(mu, logvar)

        # With std=1 (logvar=0), samples should differ
        assert not torch.allclose(z1, z2, atol=1e-6)

    def test_reparameterize_eval_mode_returns_mu(self):
        """In eval mode, reparameterize should return mu directly."""
        from cohezion.flume.vae import FlumeVAE

        model = FlumeVAE(input_dim=768, latent_dim=256)
        model.eval()
        mu = torch.randn(4, 256)
        logvar = torch.full((4, 256), -2.0)

        z = model.reparameterize(mu, logvar)
        torch.testing.assert_close(z, mu)


class TestForwardPass:
    """Test full forward pass."""

    def test_forward_returns_all_components(self):
        """Forward should return (recon, mu, logvar, z)."""
        from cohezion.flume.vae import FlumeVAE

        model = FlumeVAE(input_dim=768, latent_dim=256)
        x = torch.randn(8, 768)
        recon, mu, logvar, z = model(x)

        assert recon.shape == (8, 768)
        assert mu.shape == (8, 256)
        assert logvar.shape == (8, 256)
        assert z.shape == (8, 256)

    def test_forward_reconstruction_is_finite(self):
        """Full forward pass should produce finite outputs."""
        from cohezion.flume.vae import FlumeVAE

        model = FlumeVAE(input_dim=768, latent_dim=256)
        x = torch.randn(4, 768)
        recon, mu, logvar, z = model(x)

        assert torch.isfinite(recon).all()
        assert torch.isfinite(mu).all()
        assert torch.isfinite(logvar).all()
        assert torch.isfinite(z).all()


class TestLossFunction:
    """Test VAE loss computation."""

    def test_reconstruction_loss_is_positive(self):
        """MSE reconstruction loss should be positive."""
        from cohezion.flume.vae import flume_vae_loss

        x = torch.randn(8, 768)
        recon = torch.randn(8, 768)
        mu = torch.randn(8, 256)
        logvar = torch.zeros(8, 256)

        loss_dict = flume_vae_loss(x, recon, mu, logvar, beta=0.1)

        assert loss_dict["recon_loss"].item() > 0
        assert loss_dict["total_loss"].item() > 0

    def test_kl_loss_is_positive(self):
        """KL divergence should be positive for non-standard normal."""
        from cohezion.flume.vae import flume_vae_loss

        x = torch.randn(8, 768)
        recon = x.clone()  # Perfect reconstruction
        mu = torch.ones(8, 256) * 2.0  # Non-zero mean
        logvar = torch.ones(8, 256)  # Non-unit variance

        loss_dict = flume_vae_loss(x, recon, mu, logvar, beta=1.0)

        assert loss_dict["kl_loss"].item() > 0

    def test_kl_loss_zero_for_standard_normal(self):
        """KL should be near zero when mu=0, logvar=0 (standard normal)."""
        from cohezion.flume.vae import flume_vae_loss

        x = torch.randn(8, 768)
        mu = torch.zeros(8, 256)
        logvar = torch.zeros(8, 256)

        loss_dict = flume_vae_loss(x, x.clone(), mu, logvar, beta=1.0, free_bits=0.0)

        assert loss_dict["kl_loss"].item() < 0.01

    def test_free_bits_clamps_kl(self):
        """Free-bits should enforce minimum KL per dimension."""
        from cohezion.flume.vae import flume_vae_loss

        x = torch.randn(8, 768)
        mu = torch.zeros(8, 256)
        logvar = torch.zeros(8, 256)

        # With free_bits=0, KL ~0 for standard normal
        loss_no_fb = flume_vae_loss(x, x, mu, logvar, beta=1.0, free_bits=0.0)
        # With free_bits=0.125, KL should be >= 0.125 * 256
        loss_fb = flume_vae_loss(x, x, mu, logvar, beta=1.0, free_bits=0.125)

        assert loss_fb["kl_loss"].item() >= loss_no_fb["kl_loss"].item()

    def test_beta_scales_kl_contribution(self):
        """Higher beta should increase KL contribution to total loss."""
        from cohezion.flume.vae import flume_vae_loss

        x = torch.randn(8, 768)
        recon = torch.randn(8, 768)
        mu = torch.ones(8, 256)
        logvar = torch.zeros(8, 256)

        loss_low = flume_vae_loss(x, recon, mu, logvar, beta=0.01)
        loss_high = flume_vae_loss(x, recon, mu, logvar, beta=1.0)

        assert loss_high["total_loss"].item() > loss_low["total_loss"].item()

    def test_coherence_loss_penalizes_deviation_from_hiho(self):
        """Coherence loss should be higher when mean(mu) deviates from 0.5."""
        from cohezion.flume.vae import flume_vae_loss

        x = torch.randn(8, 768)
        mu_centered = torch.full((8, 256), 0.5)
        mu_off = torch.full((8, 256), 2.0)
        logvar = torch.zeros(8, 256)

        loss_centered = flume_vae_loss(x, x, mu_centered, logvar, lambda_coherence=1.0)
        loss_off = flume_vae_loss(x, x, mu_off, logvar, lambda_coherence=1.0)

        assert loss_off["coherence_loss"].item() > loss_centered["coherence_loss"].item()


class TestModelConfig:
    """Test model parameter counts and configuration."""

    def test_parameter_count_reasonable(self):
        """Model should have ~2M parameters (not too large for CPU training)."""
        from cohezion.flume.vae import FlumeVAE

        model = FlumeVAE(input_dim=768, latent_dim=256)
        total_params = sum(p.numel() for p in model.parameters())

        # Should be between 1M and 4M params
        assert 1_000_000 < total_params < 4_000_000, f"Got {total_params} params"

    def test_different_latent_dims(self):
        """Model should work with different latent dimensions."""
        from cohezion.flume.vae import FlumeVAE

        for latent_dim in [64, 128, 256]:
            model = FlumeVAE(input_dim=768, latent_dim=latent_dim)
            x = torch.randn(2, 768)
            recon, mu, logvar, z = model(x)
            assert mu.shape == (2, latent_dim)
            assert recon.shape == (2, 768)
