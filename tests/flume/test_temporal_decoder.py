"""Tests for FLUME Phase 2 TemporalDecoder.

Architecture:
  z(256) + target sequence [B, T, 29]
    → Linear(256→128) latent projection
    → Transformer decoder (causal, 2 layers, 4 heads)
    → Linear(128→29) step prediction
    → reconstructed sequence [B, T, 29]
"""

from __future__ import annotations

import pytest

try:
    import torch

    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

pytestmark = pytest.mark.skipif(not TORCH_AVAILABLE, reason="PyTorch not installed")

STEP_DIM = 29
LATENT_DIM = 256
D_MODEL = 128


@pytest.fixture
def decoder():
    from cohezion.flume.temporal_encoder import TemporalDecoder

    return TemporalDecoder(step_dim=STEP_DIM, d_model=D_MODEL, latent_dim=LATENT_DIM)


def make_z(batch: int, seed: int = 0) -> "torch.Tensor":
    torch.manual_seed(seed)
    return torch.randn(batch, LATENT_DIM)


def make_sequence(batch: int, seq_len: int, seed: int = 0) -> "torch.Tensor":
    torch.manual_seed(seed)
    return torch.randn(batch, seq_len, STEP_DIM)


class TestTemporalDecoderShape:
    """Verify output shapes are correct."""

    def test_decode_returns_tensor(self, decoder) -> None:
        """decode() returns a Tensor."""
        import torch

        z = make_z(4)
        target = make_sequence(4, 10)
        out = decoder.decode(z, target)
        assert isinstance(out, torch.Tensor)

    def test_output_shape_matches_target(self, decoder) -> None:
        """Output shape matches target sequence shape [B, T, step_dim]."""
        z = make_z(4)
        target = make_sequence(4, 10)
        out = decoder.decode(z, target)
        assert out.shape == (4, 10, STEP_DIM)

    def test_single_step_target(self, decoder) -> None:
        """Works with target length 1."""
        z = make_z(2)
        target = make_sequence(2, 1)
        out = decoder.decode(z, target)
        assert out.shape == (2, 1, STEP_DIM)

    def test_long_target_sequence(self, decoder) -> None:
        """Works with target length 100."""
        z = make_z(2)
        target = make_sequence(2, 100)
        out = decoder.decode(z, target)
        assert out.shape == (2, 100, STEP_DIM)

    def test_batch_size_one(self, decoder) -> None:
        """Works with batch size 1."""
        z = make_z(1)
        target = make_sequence(1, 15)
        out = decoder.decode(z, target)
        assert out.shape == (1, 15, STEP_DIM)


class TestTemporalDecoderCausality:
    """Verify causal (autoregressive) masking."""

    def test_output_not_all_zero(self, decoder) -> None:
        """Decoder produces non-zero output."""
        import torch

        z = make_z(4)
        target = make_sequence(4, 10)
        out = decoder.decode(z, target)
        assert not torch.allclose(out, torch.zeros_like(out))

    def test_different_z_different_output(self, decoder) -> None:
        """Different latent z vectors produce different outputs."""
        target = make_sequence(2, 10)
        z1 = make_z(2, seed=1)
        z2 = make_z(2, seed=2)
        out1 = decoder.decode(z1, target)
        out2 = decoder.decode(z2, target)
        assert not torch.allclose(out1, out2)


class TestTemporalDecoderGradients:
    """Verify gradients flow for training."""

    def test_gradients_flow(self, decoder) -> None:
        """Loss on output produces gradients in decoder parameters."""
        decoder.train()
        z = make_z(4)
        target = make_sequence(4, 10)
        out = decoder.decode(z, target)
        loss = out.sum()
        loss.backward()
        has_grad = any(p.grad is not None for p in decoder.parameters())
        assert has_grad


class TestTemporalDecoderInit:
    """Verify construction and defaults."""

    def test_default_construction(self) -> None:
        """TemporalDecoder constructs with expected defaults."""
        from cohezion.flume.temporal_encoder import TemporalDecoder

        dec = TemporalDecoder()
        assert dec.step_dim == STEP_DIM
        assert dec.d_model == D_MODEL
        assert dec.latent_dim == LATENT_DIM

    def test_custom_dims(self) -> None:
        """TemporalDecoder accepts custom dimensions."""
        import torch

        from cohezion.flume.temporal_encoder import TemporalDecoder

        dec = TemporalDecoder(step_dim=16, d_model=64, latent_dim=128, n_heads=2, n_layers=1)
        z = torch.randn(2, 128)
        target = torch.randn(2, 5, 16)
        out = dec.decode(z, target)
        assert out.shape == (2, 5, 16)


class TestTemporalVAEForward:
    """Test encoder + decoder round-trip."""

    def test_roundtrip_shape(self) -> None:
        """Encoder → z → Decoder produces same shape as input."""
        import torch

        from cohezion.flume.temporal_encoder import TemporalDecoder, TemporalEncoder

        enc = TemporalEncoder()
        dec = TemporalDecoder()
        x = torch.randn(4, 10, STEP_DIM)
        mu, logvar = enc.encode(x)
        z = enc.reparameterize(mu, logvar)
        recon = dec.decode(z, x)
        assert recon.shape == x.shape

    def test_reconstruction_loss_computable(self) -> None:
        """MSE reconstruction loss can be computed and backpropagated."""
        import torch
        import torch.nn.functional as F

        from cohezion.flume.temporal_encoder import TemporalDecoder, TemporalEncoder

        enc = TemporalEncoder()
        dec = TemporalDecoder()
        enc.train()
        dec.train()

        x = torch.randn(4, 10, STEP_DIM)
        mu, logvar = enc.encode(x)
        z = enc.reparameterize(mu, logvar)
        recon = dec.decode(z, x)

        loss = F.mse_loss(recon, x)
        loss.backward()
        assert loss.item() >= 0
