"""Tests for RealSkillStateDataset.

Critical invariants:
  1. Falls back to SyntheticFlumeDataset when SurrealDB is unreachable.
  2. Gaussian augmentation is only applied to continuous dims [0:29];
     the SHA-256 fingerprint region [29:256] must remain bit-exact.
  3. Dataset protocol: len() > 0, __getitem__ returns a 256D float32 tensor.
"""

from __future__ import annotations

import numpy as np
import torch

from cohezion.flume.dataset import RealSkillStateDataset


# ── Offline / fallback ────────────────────────────────────────────────────────


def test_falls_back_to_synthetic_when_surreal_offline():
    """With a nonsense URL, must not raise; data comes from SyntheticFlumeDataset."""
    ds = RealSkillStateDataset(
        n_samples=64,
        surreal_url="http://127.0.0.1:19999/sql",  # nothing listening here
        limit=10,
    )
    assert len(ds) > 0
    sample = ds[0]
    assert isinstance(sample, torch.Tensor)
    assert sample.shape == (256,)
    assert sample.dtype == torch.float32


# ── Augmentation boundary ─────────────────────────────────────────────────────


def test_augmentation_does_not_touch_fingerprint_dims():
    """Augmentation sigma applied to [0:29] must leave [29:256] untouched.

    We directly call _encode_records with a known synthetic record to get
    two encodings: with and without augmentation, then verify the fingerprint
    region is identical.
    """
    ds_no_aug = RealSkillStateDataset.__new__(RealSkillStateDataset)
    ds_no_aug.z_dim = 256
    ds_no_aug._rng = np.random.default_rng(0)

    ds_aug = RealSkillStateDataset.__new__(RealSkillStateDataset)
    ds_aug.z_dim = 256
    ds_aug._rng = np.random.default_rng(42)

    records = [
        {
            "task_id": "test-001",
            "category": "code",
            "success": True,
            "tokens": 512,
            "node": "npu",
            "model": "llama3.2-1b-FLM",
            "quality_score": 0.9,
            "elapsed_ms": 120,
            "recorded_at": "2026-06-17T00:00:00Z",
        }
    ]

    vecs_no_aug = ds_no_aug._encode_records(records, augment_sigma=0.0)
    vecs_aug = ds_aug._encode_records(records, augment_sigma=0.05)

    assert len(vecs_no_aug) == 1
    assert len(vecs_aug) == 1

    v_base = vecs_no_aug[0]
    v_aug = vecs_aug[0]

    # Fingerprint region must be bit-exact
    np.testing.assert_array_equal(
        v_base[29:],
        v_aug[29:],
        err_msg="SHA-256 fingerprint dims [29:256] must not be modified by augmentation",
    )

    # Continuous dims may differ (augment_sigma=0.05 is large enough to guarantee change)
    assert not np.allclose(v_base[:29], v_aug[:29]), (
        "Continuous dims [0:29] should differ after augmentation with sigma=0.05"
    )


# ── Dataset protocol ──────────────────────────────────────────────────────────


def test_dataset_protocol_offline():
    """len() and __getitem__ work correctly in offline-fallback mode."""
    n = 128
    ds = RealSkillStateDataset(
        n_samples=n,
        surreal_url="http://127.0.0.1:19999/sql",
        limit=10,
    )
    assert len(ds) == n
    for idx in [0, n // 2, n - 1]:
        t = ds[idx]
        assert t.shape == (256,)
        assert t.dtype == torch.float32
        assert torch.isfinite(t).all()
