"""Tests for FlumeTwoTrack — two-track structural/semantic FLUME VAE split."""

import torch
import pytest

from cohezion.flume.vae import FlumeVAE
from cohezion.flume.flume_two_track import FlumeTwoTrack, run_twotrack_smoke_test


@pytest.fixture()
def small_tt() -> FlumeTwoTrack:
    """Small two-track VAE for fast tests: input_dim=16, latent_dim=8, structural=4."""
    base = FlumeVAE(input_dim=16, latent_dim=8)
    base.eval()
    return FlumeTwoTrack(base, structural_dim=4)


def test_encode_splits_dims_correctly(small_tt: FlumeTwoTrack) -> None:
    """encode() must return 4 tensors with structural+semantic dims summing to latent_dim."""
    x = torch.randn(5, 16)
    mu, log_var, mu_s, mu_e = small_tt.encode(x)
    # full latent
    assert mu.shape == (5, 8)
    assert log_var.shape == (5, 8)
    # structural track
    assert mu_s.shape == (5, 4)
    # semantic track
    assert mu_e.shape == (5, 4)
    # must be exact slices of mu — not independent encodings
    assert torch.equal(mu_s, mu[:, :4])
    assert torch.equal(mu_e, mu[:, 4:])


def test_interpolate_swap_structural_takes_structural_from_z1(
    small_tt: FlumeTwoTrack,
) -> None:
    """interpolate(z1, z2, swap_structural=True) must use structural dims from z1."""
    z1 = torch.zeros(3, 8)
    z2 = torch.ones(3, 8)
    result = small_tt.interpolate(z1, z2, swap_structural=True)
    # structural (first 4 dims) from z1 → should be 0
    assert torch.all(result[:, :4] == 0.0), "structural dims must come from z1"
    # semantic (last 4 dims) from z2 → should be 1
    assert torch.all(result[:, 4:] == 1.0), "semantic dims must come from z2"


def test_structural_regularizer_returns_non_positive_scalar(
    small_tt: FlumeTwoTrack,
) -> None:
    """structural_regularizer() must return a scalar tensor ≤ 0."""
    mu_s = torch.randn(10, 4)  # batch with variance → regularizer is meaningful
    reg = small_tt.structural_regularizer(mu_s)
    assert reg.dim() == 0, "must be a scalar (0-dim tensor)"
    # Variance is always ≥ 0, so negated value is ≤ 0
    assert float(reg) <= 0.0, f"regularizer must be ≤ 0, got {float(reg)}"


def test_smoke_test_passes() -> None:
    """run_twotrack_smoke_test() must return smoke_passed=True with correct dims."""
    result = run_twotrack_smoke_test()
    assert result["smoke_passed"] is True
    assert result["structural_dim"] == 4
    assert result["semantic_dim"] == 4
    assert result["structural_dim"] + result["semantic_dim"] == 8
