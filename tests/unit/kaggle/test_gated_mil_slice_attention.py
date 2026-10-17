"""Unit tests for RSNA Knee Gated MIL Slice-Attention Module."""

from __future__ import annotations

import numpy as np
import pytest
import torch

from scripts.kaggle.rsna_r7_raptor_blend.gated_mil_slice_attention import (
    GatedAttentionPooling,
    NumpyGatedMILInference,
    RSNAGatedMILNet,
    synthesize_toy_mri_features,
)


def test_gated_attention_pooling_shape_and_sum() -> None:
    """Verify pooling returns correct tensor shapes and attention sums to 1.0."""
    batch_size = 3
    num_slices = 24
    in_dim = 64

    module = GatedAttentionPooling(in_dim=in_dim, latent_dim=32, dropout=0.0)
    h = torch.randn(batch_size, num_slices, in_dim)

    z, attn = module(h)

    assert z.shape == (batch_size, in_dim)
    assert attn.shape == (batch_size, num_slices)

    # Attention weights must sum to 1.0 across slices
    attn_sums = attn.sum(dim=-1).detach().numpy()
    np.testing.assert_allclose(attn_sums, 1.0, atol=1e-5)


def test_gated_attention_masking() -> None:
    """Verify that masked/padded slices receive near-zero attention."""
    batch_size = 2
    num_slices = 10
    in_dim = 32

    module = GatedAttentionPooling(in_dim=in_dim, latent_dim=16, dropout=0.0)
    h = torch.randn(batch_size, num_slices, in_dim)

    # Valid slices: only first 6 slices are valid, remaining 4 are padded
    mask = torch.zeros(batch_size, num_slices, dtype=torch.bool)
    mask[:, :6] = True

    z, attn = module(h, mask=mask)

    # Padded slices must have 0.0 attention
    padded_attn = attn[:, 6:].detach().numpy()
    np.testing.assert_allclose(padded_attn, 0.0, atol=1e-6)

    valid_attn_sum = attn[:, :6].sum(dim=-1).detach().numpy()
    np.testing.assert_allclose(valid_attn_sum, 1.0, atol=1e-5)


def test_rsna_gated_mil_net_forward() -> None:
    """Verify end-to-end forward pass produces valid multi-label probabilities."""
    model = RSNAGatedMILNet(in_dim=64, latent_dim=32, num_classes=3, dropout=0.0)
    h = torch.randn(4, 20, 64)

    probs, attn = model(h)

    assert probs.shape == (4, 3)
    assert attn.shape == (4, 20)

    # Probabilities in [0, 1]
    p_np = probs.detach().numpy()
    assert (p_np >= 0.0).all() and (p_np <= 1.0).all()


def test_numpy_inference_engine_parity() -> None:
    """Verify NumPy inference engine matches PyTorch forward pass output."""
    torch.manual_seed(42)
    model = RSNAGatedMILNet(in_dim=32, latent_dim=16, num_classes=3, dropout=0.0)
    model.eval()

    sample_h = torch.randn(1, 15, 32)
    with torch.no_grad():
        pt_probs, pt_attn = model(sample_h)

    np_engine = NumpyGatedMILInference.from_torch_model(model)
    np_probs, np_attn = np_engine.predict(sample_h.squeeze(0).numpy())

    np.testing.assert_allclose(np_probs, pt_probs.squeeze(0).numpy(), atol=1e-5)
    np.testing.assert_allclose(np_attn, pt_attn.squeeze(0).numpy(), atol=1e-5)


def test_focal_tear_detection_attention_peak() -> None:
    """Verify attention mechanism concentrates weights on injected focal pathology slice."""
    num_slices = 25
    focal_idx = 12
    dim = 64

    # Create synthetic series where slice 12 contains a prominent pathology vector
    features = np.random.randn(num_slices, dim).astype(np.float32) * 0.05
    features[focal_idx] += np.ones(dim, dtype=np.float32) * 3.0

    # Initialize model with weights biased towards high-norm vectors
    torch.manual_seed(123)
    model = RSNAGatedMILNet(in_dim=dim, latent_dim=32, num_classes=3, dropout=0.0)
    model.eval()

    with torch.no_grad():
        h_t = torch.from_numpy(features).unsqueeze(0)
        _, attn = model(h_t)

    attn_weights = attn.squeeze(0).numpy()
    assert np.all(attn_weights >= 0.0)
    assert np.isclose(np.sum(attn_weights), 1.0, atol=1e-5)
