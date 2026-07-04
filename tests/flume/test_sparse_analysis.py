"""Unit tests for SparseLatentAnalysis — FLUME sparse feature decomposition.

Test inventory
--------------
test_fit_encode_roundtrip
    Numpy path: matching pursuit must reduce reconstruction error vs. zero code.
test_top_features_returns_k_items
    top_features(k=3) returns exactly 3 (index, activation) pairs, sorted by
    |activation| descending.
test_handles_zero_vector
    encode() and top_features() must not raise for an all-zero input.
test_numpy_fallback_path
    _force_numpy=True bypasses sklearn; active atoms <= max_active bound.
"""

from __future__ import annotations

import numpy as np


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_latents(n_samples: int = 40, n_features: int = 64, seed: int = 0) -> np.ndarray:
    return np.random.default_rng(seed).standard_normal((n_samples, n_features))


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_fit_encode_roundtrip() -> None:
    """Matching pursuit must produce a code that reduces reconstruction error."""
    from cohezion.flume.sparse_analysis import SparseLatentAnalysis

    rng = np.random.default_rng(0)
    latents = rng.standard_normal((50, 64)).astype(np.float64)
    z = rng.standard_normal(64).astype(np.float64)

    # Use _force_numpy so matching pursuit is guaranteed to make ≥1 active step
    # (sklearn lasso_lars may legitimately zero-out sparse codes on Gaussian noise)
    model = SparseLatentAnalysis(n_atoms=32, sparsity_target=0.1, _force_numpy=True)
    model.fit(latents)
    alpha = model.encode(z)

    assert alpha.shape == (32,), f"Expected shape (32,), got {alpha.shape}"

    # Discriminating assertion: encoding must have done real work
    assert model._dictionary is not None
    recon = model._dictionary.T @ alpha
    error_encoded = float(np.linalg.norm(z - recon))
    error_zero = float(np.linalg.norm(z))

    assert error_encoded < error_zero, (
        f"Encoding did not reduce reconstruction error "
        f"({error_encoded:.4f} >= {error_zero:.4f})"
    )
    assert np.count_nonzero(alpha) >= 1, "At least one atom must be active"


def test_top_features_returns_k_items() -> None:
    """top_features(k=3) returns exactly 3 items sorted by |activation| desc."""
    from cohezion.flume.sparse_analysis import SparseLatentAnalysis

    rng = np.random.default_rng(1)
    latents = rng.standard_normal((40, 64)).astype(np.float64)
    z = rng.standard_normal(64).astype(np.float64)

    model = SparseLatentAnalysis(n_atoms=16, sparsity_target=0.3, _force_numpy=True)
    model.fit(latents)
    features = model.top_features(z, k=3)

    assert len(features) == 3, f"Expected 3 features, got {len(features)}"

    for atom_idx, activation in features:
        assert isinstance(atom_idx, int), f"Index must be int, got {type(atom_idx)}"
        assert isinstance(activation, float), f"Activation must be float, got {type(activation)}"

    # Must be sorted by |activation| descending (discriminating: wrong argsort order would fail)
    abs_activations = [abs(v) for _, v in features]
    assert abs_activations == sorted(abs_activations, reverse=True), (
        f"Features not sorted by |activation|: {abs_activations}"
    )


def test_handles_zero_vector() -> None:
    """encode() and top_features() must not raise for an all-zero input vector."""
    from cohezion.flume.sparse_analysis import SparseLatentAnalysis

    latents = _make_latents(n_samples=30, n_features=64, seed=2)
    z_zero = np.zeros(64)

    model = SparseLatentAnalysis(n_atoms=16, sparsity_target=0.1, _force_numpy=True)
    model.fit(latents)

    # No exception expected
    alpha = model.encode(z_zero)
    assert alpha.shape == (16,), f"Expected shape (16,), got {alpha.shape}"

    # top_features must still return exactly k items (activations will be 0.0)
    features = model.top_features(z_zero, k=5)
    assert len(features) == 5


def test_numpy_fallback_path() -> None:
    """_force_numpy=True bypasses sklearn; active atoms bounded by sparsity_target."""
    from cohezion.flume.sparse_analysis import SparseLatentAnalysis

    rng = np.random.default_rng(3)
    latents = rng.standard_normal((30, 64)).astype(np.float64)
    z = rng.standard_normal(64).astype(np.float64)

    model = SparseLatentAnalysis(n_atoms=20, sparsity_target=0.2, _force_numpy=True)

    assert not model._use_sklearn, (
        "_use_sklearn should be False when _force_numpy=True"
    )

    model.fit(latents)
    alpha = model.encode(z)

    assert alpha.shape == (20,), f"Expected shape (20,), got {alpha.shape}"

    # Matching pursuit makes at most max_active = int(0.2 * 20) = 4 steps
    max_active = max(1, int(0.2 * 20))
    n_active = int(np.count_nonzero(alpha))
    assert n_active <= max_active, (
        f"numpy path produced {n_active} active atoms, expected ≤ {max_active}"
    )
