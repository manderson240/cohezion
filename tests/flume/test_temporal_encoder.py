"""Tests for FLUME Phase 2 TemporalEncoder.

Architecture:
  sequence of (12D state + 12D metrics + 5D op_type) steps → [T, 29]
    → Linear(29→128) step embedding + positional encoding
    → 2-layer 4-head Transformer encoder
    → attention pooling
    → mu(256), logvar(256)
"""

from __future__ import annotations

import pytest
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import torch


try:
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

pytestmark = pytest.mark.skipif(not TORCH_AVAILABLE, reason="PyTorch not installed")


STEP_DIM = 29  # 12 trajectory + 12 metrics + 5 op_type
LATENT_DIM = 256
D_MODEL = 128


@pytest.fixture
def encoder():
    from cohezion.flume.temporal_encoder import TemporalEncoder

    return TemporalEncoder(step_dim=STEP_DIM, d_model=D_MODEL, latent_dim=LATENT_DIM)


def make_sequence(batch: int, seq_len: int, seed: int = 42) -> torch.Tensor:
    """Create a random batch of trajectory sequences."""
    import torch

    rng = torch.Generator()
    rng.manual_seed(seed)
    return torch.randn(batch, seq_len, STEP_DIM, generator=rng)


class TestTemporalEncoderShape:
    """Verify output shapes are correct."""

    def test_encode_returns_mu_and_logvar(self, encoder) -> None:
        """encode() returns (mu, logvar) tuple."""
        import torch

        x = make_sequence(4, 10)
        mu, logvar = encoder.encode(x)
        assert isinstance(mu, torch.Tensor)
        assert isinstance(logvar, torch.Tensor)

    def test_mu_shape(self, encoder) -> None:
        """mu shape is (batch, latent_dim)."""
        x = make_sequence(4, 10)
        mu, _ = encoder.encode(x)
        assert mu.shape == (4, LATENT_DIM)

    def test_logvar_shape(self, encoder) -> None:
        """logvar shape is (batch, latent_dim)."""
        x = make_sequence(4, 10)
        _, logvar = encoder.encode(x)
        assert logvar.shape == (4, LATENT_DIM)

    def test_single_step_sequence(self, encoder) -> None:
        """Works with sequence length 1."""
        x = make_sequence(2, 1)
        mu, logvar = encoder.encode(x)
        assert mu.shape == (2, LATENT_DIM)

    def test_long_sequence(self, encoder) -> None:
        """Works with sequence length 100."""
        x = make_sequence(2, 100)
        mu, _ = encoder.encode(x)
        assert mu.shape == (2, LATENT_DIM)

    def test_batch_size_one(self, encoder) -> None:
        """Works with batch size 1."""
        x = make_sequence(1, 15)
        mu, _ = encoder.encode(x)
        assert mu.shape == (1, LATENT_DIM)


class TestTemporalEncoderVariational:
    """Verify VAE properties."""

    def test_reparameterize_stochastic(self, encoder) -> None:
        """Two reparameterize calls from same mu/logvar give different z."""
        import torch

        x = make_sequence(4, 10)
        mu, logvar = encoder.encode(x)
        z1 = encoder.reparameterize(mu, logvar)
        z2 = encoder.reparameterize(mu, logvar)
        # Different due to random noise
        assert not torch.allclose(z1, z2)

    def test_reparameterize_shape(self, encoder) -> None:
        """reparameterize() returns (batch, latent_dim)."""
        x = make_sequence(4, 10)
        mu, logvar = encoder.encode(x)
        z = encoder.reparameterize(mu, logvar)
        assert z.shape == (4, LATENT_DIM)

    def test_eval_mode_deterministic(self, encoder) -> None:
        """In eval mode, encode is deterministic (mu returned directly)."""
        import torch

        encoder.eval()
        x = make_sequence(4, 10, seed=7)
        mu1, lv1 = encoder.encode(x)
        mu2, lv2 = encoder.encode(x)
        torch.testing.assert_close(mu1, mu2)
        torch.testing.assert_close(lv1, lv2)
        encoder.train()

    def test_mu_not_all_zero(self, encoder) -> None:
        """mu values should not all be zero (model should encode something)."""
        import torch

        x = make_sequence(4, 10)
        mu, _ = encoder.encode(x)
        assert not torch.allclose(mu, torch.zeros_like(mu))


class TestTemporalEncoderPaddingMask:
    """Verify padding mask is handled correctly."""

    def test_padding_mask_accepted(self, encoder) -> None:
        """encode() accepts an optional padding_mask argument."""
        import torch

        x = make_sequence(4, 10)
        # True = position is padding (ignore), False = valid
        mask = torch.zeros(4, 10, dtype=torch.bool)
        mask[:, 8:] = True  # last 2 positions are padding
        mu, _ = encoder.encode(x, padding_mask=mask)
        assert mu.shape == (4, LATENT_DIM)

    def test_different_seq_lengths_with_mask(self, encoder) -> None:
        """Batch with different valid lengths (rest padded) still works."""
        import torch

        batch, max_len = 3, 12
        x = make_sequence(batch, max_len)
        mask = torch.zeros(batch, max_len, dtype=torch.bool)
        # sequence lengths: 5, 8, 12
        valid_lens = [5, 8, 12]
        for i, vl in enumerate(valid_lens):
            mask[i, vl:] = True
        mu, _ = encoder.encode(x, padding_mask=mask)
        assert mu.shape == (batch, LATENT_DIM)


class TestTemporalEncoderGradients:
    """Verify gradients flow correctly for training."""

    def test_gradients_flow_through_mu(self, encoder) -> None:
        """Loss on mu produces gradients in encoder parameters."""

        encoder.train()
        x = make_sequence(4, 10)
        x.requires_grad_(False)
        mu, logvar = encoder.encode(x)
        loss = mu.sum() + logvar.sum()
        loss.backward()
        # At least one parameter should have a non-None gradient
        has_grad = any(p.grad is not None for p in encoder.parameters())
        assert has_grad


class TestTemporalEncoderInit:
    """Verify construction and defaults."""

    def test_default_construction(self) -> None:
        """TemporalEncoder constructs with expected defaults."""
        from cohezion.flume.temporal_encoder import TemporalEncoder

        enc = TemporalEncoder()
        assert enc.step_dim == STEP_DIM
        assert enc.d_model == D_MODEL
        assert enc.latent_dim == LATENT_DIM

    def test_custom_dims(self) -> None:
        """TemporalEncoder accepts custom dimensions."""
        import torch

        from cohezion.flume.temporal_encoder import TemporalEncoder

        enc = TemporalEncoder(step_dim=16, d_model=64, latent_dim=128, n_heads=2, n_layers=1)
        x = torch.randn(2, 5, 16)
        mu, logvar = enc.encode(x)
        assert mu.shape == (2, 128)
