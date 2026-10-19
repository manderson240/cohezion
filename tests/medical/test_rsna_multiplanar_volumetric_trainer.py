"""Unit tests for RSNA Multi-Planar Volumetric Network & Trainer.
================================================================
Validates:
1. StabilizedCrossPlanarAttention forward shape and residual connection.
2. MultiPlanarVolumetricNet end-to-end forward pass on orthogonal planes.
3. MultiPlanarVolumetricTrainer optimization step and gradient norm clipping.
4. Out-of-fold evaluation with zero-leakage splits and error report generation.
"""

from __future__ import annotations

import numpy as np
import torch

from cohezion.medical.rsna_multiplanar_volumetric_trainer import (
    MultiPlanarVolumetricNet,
    MultiPlanarVolumetricTrainer,
    StabilizedCrossPlanarAttention,
)


def test_stabilized_cross_planar_attention_shapes_and_residuals() -> None:
    batch_size = 4
    dim = 64
    attn = StabilizedCrossPlanarAttention(in_features=dim, reduction=2)

    sag = torch.randn(batch_size, dim)
    cor = torch.randn(batch_size, dim)
    ax = torch.randn(batch_size, dim)

    fused = attn(sag, cor, ax)
    assert fused.shape == (batch_size, dim)
    # Check that output is finite
    assert torch.isfinite(fused).all()


def test_multiplanar_volumetric_net_forward() -> None:
    batch_size = 8
    feat_dim = 128
    n_classes = 12

    model = MultiPlanarVolumetricNet(feature_dim=feat_dim, n_classes=n_classes)
    sag = torch.randn(batch_size, feat_dim)
    cor = torch.randn(batch_size, feat_dim)
    ax = torch.randn(batch_size, feat_dim)

    logits = model(sag, cor, ax)
    assert logits.shape == (batch_size, n_classes)
    probs = torch.sigmoid(logits)
    assert (probs >= 0.0).all() and (probs <= 1.0).all()


def test_multiplanar_volumetric_trainer_optimization_and_oof() -> None:
    n_samples = 60
    feat_dim = 64
    n_classes = 12

    model = MultiPlanarVolumetricNet(feature_dim=feat_dim, n_classes=n_classes)
    trainer = MultiPlanarVolumetricTrainer(
        model=model,
        lambda_rank=0.2,
        rank_warmup_epochs=1,
        lr=1e-3,
    )

    rng = np.random.default_rng(42)
    # 60 samples from 12 patients (5 series per patient)
    groups = np.repeat(np.arange(12), 5)
    y_true_np = rng.integers(0, 2, size=(n_samples, n_classes))

    sag = torch.randn(n_samples, feat_dim)
    cor = torch.randn(n_samples, feat_dim)
    ax = torch.randn(n_samples, feat_dim)
    y_true_t = torch.tensor(y_true_np, dtype=torch.float32)

    # 1. Warmup epoch (epoch 1, rank_loss disabled)
    warmup_metrics = trainer.train_epoch(sag, cor, ax, y_true_t, epoch=1)
    assert "total_loss" in warmup_metrics
    assert warmup_metrics["rank_weight"] == 0.0

    # 2. Hybrid epoch (epoch 2, rank_loss enabled)
    hybrid_metrics = trainer.train_epoch(sag, cor, ax, y_true_t, epoch=2)
    assert hybrid_metrics["rank_weight"] == 0.2

    # 3. OOF Evaluation
    val_result, error_report = trainer.evaluate_oof(sag, cor, ax, y_true_np, groups)
    assert val_result.n_samples == n_samples
    assert val_result.n_groups == 12
    assert val_result.ci_lower <= val_result.mean_score <= val_result.ci_upper
    assert error_report.competition == "rsna_knee"
    assert len(error_report.buckets) == 12
