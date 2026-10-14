#!/usr/bin/env python3
"""Unit tests for RSNA Cross-Planar Attention & Calibration Module."""

import numpy as np
import torch
import pytest

from cohezion.models.rsna_cross_planar_attention import (
    CrossPlanarAttention,
    ledoit_wolf_shrinkage,
    soft_kolmogorov_projection,
)


def test_cross_planar_attention_forward():
    B, C, H, W = 2, 64, 16, 16
    planes = {
        "sagittal": torch.randn(B, C, H, W),
        "coronal": torch.randn(B, C, H, W),
        "axial": torch.randn(B, C, H, W),
    }

    model = CrossPlanarAttention(in_channels=C, reduction=4)
    out = model(planes)

    assert out.shape == (B, C, H, W)
    assert not torch.isnan(out).any()
    assert not torch.isinf(out).any()


def test_ledoit_wolf_shrinkage():
    np.random.seed(42)
    X = np.random.randn(50, 5)
    X -= X.mean(axis=0)

    cov, shrinkage = ledoit_wolf_shrinkage(X)
    assert cov.shape == (5, 5)
    assert 0.0 <= shrinkage <= 1.0
    # Symmetric and positive semi-definite
    assert np.allclose(cov, cov.T)
    eigenvalues = np.linalg.eigvalsh(cov)
    assert np.all(eigenvalues >= -1e-10)


def test_soft_kolmogorov_projection():
    N = 100
    p_raw = np.random.uniform(0.1, 0.4, N)
    # Severe subcondition violations: some subconditions are 0.90 while p_raw is 0.20
    conds = np.random.uniform(0.1, 0.9, (N, 4))

    projected = soft_kolmogorov_projection(p_raw, conds)
    assert len(projected) == N
    assert (projected >= 0.0).all() and (projected <= 1.0).all()
    # Projected Abnormal should be significantly higher than p_raw when subconditions are high
    high_sub_idx = conds.max(axis=1) > 0.8
    assert (projected[high_sub_idx] > p_raw[high_sub_idx]).all()
