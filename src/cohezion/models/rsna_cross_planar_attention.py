#!/usr/bin/env python3
"""RSNA Knee MRI: 3D Cross-Planar Attention & Ledoit-Wolf Calibration Module
===========================================================================
Fuses orthogonal planes (Sagittal × Coronal × Axial) through multi-planar
channel-wise co-attention and stabilizes multi-label probability covariance
using Ledoit-Wolf optimal shrinkage and Noisy-OR Kolmogorov projection.
"""

from __future__ import annotations

from typing import Dict, Tuple
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F


class CrossPlanarAttention(nn.Module):
    """Jointly fuses orthogonal MRI planes (Sagittal, Coronal, Axial).

    Architecture:
        1. Global Average Pooling over each plane feature map -> (B, C)
        2. Plane descriptor stacking -> (B, 3, C)
        3. Bottleneck MLP with Softmax gating over planes -> (B, 3, C)
        4. Broadcast plane modulation and elementwise sum -> (B, C, H, W)
    """

    def __init__(self, in_channels: int, reduction: int = 4) -> None:
        super().__init__()
        self.in_channels = in_channels
        self.reduction = max(1, reduction)
        self.global_pool = nn.AdaptiveAvgPool2d(1)
        self.fc1 = nn.Linear(in_channels, in_channels // self.reduction, bias=False)
        self.fc2 = nn.Linear(in_channels // self.reduction, in_channels, bias=False)
        self.softmax = nn.Softmax(dim=1)

    def forward(self, planes: Dict[str, torch.Tensor]) -> torch.Tensor:
        """Forward pass fusing Sagittal, Coronal, and Axial planes.

        Args:
            planes: Dictionary containing 'sagittal', 'coronal', 'axial'
                    tensors of shape (B, C, H, W).

        Returns:
            Fused tensor of shape (B, C, H, W).
        """
        sag = planes["sagittal"]
        cor = planes["coronal"]
        ax = planes["axial"]

        descriptors = [self.global_pool(p).view(p.size(0), -1) for p in [sag, cor, ax]]
        desc_stack = torch.stack(descriptors, dim=1)  # (B, 3, C)

        attn = self.fc2(F.relu(self.fc1(desc_stack)))  # (B, 3, C)
        attn = self.softmax(attn)  # (B, 3, C)

        attn_sag = attn[:, 0, :].unsqueeze(-1).unsqueeze(-1)
        attn_cor = attn[:, 1, :].unsqueeze(-1).unsqueeze(-1)
        attn_ax = attn[:, 2, :].unsqueeze(-1).unsqueeze(-1)

        fused = sag * attn_sag + cor * attn_cor + ax * attn_ax
        return fused


def ledoit_wolf_shrinkage(X: np.ndarray) -> Tuple[np.ndarray, float]:
    """Computes Ledoit-Wolf optimal shrinkage covariance matrix.

    Shrinks sample covariance S toward structured identity target T = mu * I:
        Sigma* = (1 - lambda*) S + lambda* T

    Args:
        X: Sample matrix of shape (n_samples, n_features), centered.

    Returns:
        Tuple of (shrunk_covariance_matrix, optimal_shrinkage_intensity).
    """
    n_samples, n_features = X.shape
    if n_samples <= 1:
        return np.eye(n_features), 1.0

    # Sample covariance
    S = np.dot(X.T, X) / n_samples
    mu = np.trace(S) / n_features
    delta = S - mu * np.eye(n_features)

    # Frobenius norm squared of delta
    gamma = float(np.sum(delta ** 2))
    if gamma < 1e-12:
        return S, 0.0

    # Asymptotic variance pi
    X2 = X ** 2
    phi = np.dot(X2.T, X2) / n_samples - S ** 2
    pi = float(np.sum(phi))

    # Optimal shrinkage intensity lambda*
    shrinkage = max(0.0, min(1.0, (pi / n_samples) / gamma))
    shrunk_cov = (1.0 - shrinkage) * S + shrinkage * mu * np.eye(n_features)
    return shrunk_cov, shrinkage


def soft_kolmogorov_projection(
    p_abnormal_raw: np.ndarray,
    condition_probs: np.ndarray,
    weights: Tuple[float, float, float] = (0.40, 0.35, 0.25)
) -> np.ndarray:
    """Enforces probabilistic Soft Kolmogorov calibration on multi-condition outputs.

    Combines raw Abnormal probability, maximum subcondition probability, and
    Noisy-OR failure probability to ensure medical consistency without flat ties:
        P(Abnormal) = clip(w1 * P_raw + w2 * max_k(P_k) + w3 * (1 - prod_k(1 - P_k)), 0, 1)

    Args:
        p_abnormal_raw: 1D array of uncalibrated Abnormal predictions.
        condition_probs: 2D array (N, K) of sub-condition predictions.
        weights: Tuple of 3 weights summing to 1.0.

    Returns:
        1D calibrated array for Abnormal condition.
    """
    w1, w2, w3 = weights
    sub_max = np.max(condition_probs, axis=1)
    clipped_sub = np.clip(condition_probs, 0.0, 0.99)
    noisy_or = 1.0 - np.prod(1.0 - clipped_sub, axis=1)

    calibrated = w1 * p_abnormal_raw + w2 * sub_max + w3 * noisy_or
    return np.clip(calibrated, 0.0, 1.0)
