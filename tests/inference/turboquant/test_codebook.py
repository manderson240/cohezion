"""Tests for cohezion.inference.turboquant.codebook.

Covers the Beta-distribution PDF (beta_pdf), the Lloyd-Max codebook solver
(compute_lloyd_max_codebook), the disk/in-memory cache (get_codebook), and the
torch-tensor accessor (get_codebook_tensors).
"""

import json
import os

import numpy as np
import pytest
import torch
from scipy import integrate

from cohezion.inference.turboquant import codebook as cb_mod
from cohezion.inference.turboquant.codebook import (
    beta_pdf,
    compute_lloyd_max_codebook,
    get_codebook,
    get_codebook_tensors,
)


# ── beta_pdf ────────────────────────────────────────────────────────────────


def test_beta_pdf_d3_is_uniform_half():
    # At d=3 the exponent (d-3)/2 == 0, so (1-x^2)^0 == 1 and the PDF collapses
    # to its constant log_const = gammaln(1.5) - 0.5*log(pi) - gammaln(1) = -log(2),
    # i.e. exactly 0.5 for every x in [-1, 1].
    xs = np.array([-1.0, -0.5, -0.1, 0.0, 0.1, 0.5, 1.0])
    result = beta_pdf(xs, d=3)
    assert result == pytest.approx(0.5, abs=1e-12)


def test_beta_pdf_integrates_to_one():
    for d in (3, 8):
        total, _ = integrate.quad(lambda x, d=d: beta_pdf(np.array([x]), d)[0], -1.0, 1.0)
        assert total == pytest.approx(1.0, abs=1e-6)


def test_beta_pdf_symmetric_about_zero():
    xs = np.array([0.05, 0.2, 0.4, 0.6, 0.8, 0.95])
    for d in (3, 8, 64):
        assert beta_pdf(-xs, d) == pytest.approx(beta_pdf(xs, d))


def test_beta_pdf_boundaries_finite_via_clip():
    # x = +-1 is clipped to [-1+1e-15, 1-1e-15] (source line 30), so no -inf/nan.
    result = beta_pdf(np.array([-1.0, 1.0]), d=3)
    assert np.all(np.isfinite(result))
    assert np.all(result > 0.0)
    assert result == pytest.approx(0.5, abs=1e-12)


def test_beta_pdf_vectorized_over_array():
    xs = np.linspace(-0.9, 0.9, 11)
    result = beta_pdf(xs, d=8)
    assert isinstance(result, np.ndarray)
    assert result.shape == xs.shape


def test_beta_pdf_empty_array_returns_empty():
    result = beta_pdf(np.array([]), d=3)
    assert isinstance(result, np.ndarray)
    assert result.shape == (0,)


def test_beta_pdf_raises_for_d_equals_2():
    with pytest.raises(ValueError, match="too small"):
        beta_pdf(np.array([0.0]), d=2)


def test_beta_pdf_d3_succeeds_boundary():
    # d=3 is the smallest accepted dimension just above the d<=2 guard.
    result = beta_pdf(np.array([0.0]), d=3)
    assert np.all(np.isfinite(result))


def test_beta_pdf_raises_for_nonpositive_d():
    for d in (0, -1):
        with pytest.raises(ValueError, match="too small"):
            beta_pdf(np.array([0.0]), d=d)


# ── compute_lloyd_max_codebook ──────────────────────────────────────────────


def test_compute_codebook_return_keys():
    cb = compute_lloyd_max_codebook(d=8, bits=1, max_iter=2)
    assert set(cb.keys()) == {
        "centroids",
        "boundaries",
        "mse_per_coord",
        "mse_total",
        "d",
        "bits",
    }


def test_compute_codebook_centroid_and_boundary_counts():
    bits = 1
    cb = compute_lloyd_max_codebook(d=8, bits=bits, max_iter=2)
    assert len(cb["centroids"]) == 2**bits
    assert len(cb["boundaries"]) == 2**bits + 1


def test_compute_codebook_boundary_endpoints():
    cb = compute_lloyd_max_codebook(d=8, bits=1, max_iter=2)
    assert cb["boundaries"][0] == -1.0
    assert cb["boundaries"][-1] == 1.0


def test_compute_codebook_centroids_sorted_and_symmetric():
    cb = compute_lloyd_max_codebook(d=8, bits=1, max_iter=5)
    centroids = np.array(cb["centroids"])
    # ascending order
    assert np.all(np.diff(centroids) > 0)
    # approximately symmetric about 0: centroids ~= -reversed(centroids)
    assert centroids == pytest.approx(-centroids[::-1], abs=1e-6)


def test_compute_codebook_mse_total_equals_per_coord_times_d():
    d = 8
    cb = compute_lloyd_max_codebook(d=d, bits=1, max_iter=2)
    assert cb["mse_total"] == pytest.approx(cb["mse_per_coord"] * d)
    assert isinstance(cb["mse_per_coord"], float)
    assert np.isfinite(cb["mse_per_coord"])
    assert cb["mse_per_coord"] >= 0.0


def test_compute_codebook_respects_max_iter_param():
    cb = compute_lloyd_max_codebook(d=8, bits=1, max_iter=2, tol=1e-6)
    assert set(cb.keys()) == {
        "centroids",
        "boundaries",
        "mse_per_coord",
        "mse_total",
        "d",
        "bits",
    }


def test_compute_codebook_propagates_value_error_for_small_d():
    # beta_pdf is invoked during centroid initialization (source line 86),
    # so the d<=2 guard propagates out of compute_lloyd_max_codebook.
    with pytest.raises(ValueError, match="too small"):
        compute_lloyd_max_codebook(d=2, bits=1)


def test_compute_codebook_bits_zero_single_cluster():
    cb = compute_lloyd_max_codebook(d=8, bits=0, max_iter=2)
    assert len(cb["centroids"]) == 1
    assert cb["centroids"][0] == pytest.approx(0.0, abs=1e-2)
    assert len(cb["boundaries"]) == 2
    assert cb["boundaries"] == [-1.0, 1.0]


# ── get_codebook (cache + disk) ─────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _isolate_codebook_globals(tmp_path, monkeypatch):
    """Save/restore module-global cache and redirect the codebook dir to tmp_path.

    Prevents the singleton in-memory cache from leaking across tests and stops any
    test from writing JSON into the repo source tree.
    """
    saved_cache = dict(cb_mod._CODEBOOK_CACHE)
    saved_dir = cb_mod._CODEBOOK_DIR
    cb_mod._CODEBOOK_CACHE.clear()
    monkeypatch.setattr(cb_mod, "_CODEBOOK_DIR", str(tmp_path / "codebooks"))
    try:
        yield
    finally:
        cb_mod._CODEBOOK_CACHE.clear()
        cb_mod._CODEBOOK_CACHE.update(saved_cache)
        cb_mod._CODEBOOK_DIR = saved_dir


def test_get_codebook_in_memory_cache_hit_skips_recompute(monkeypatch):
    sentinel = {"centroids": [0.0], "boundaries": [-1.0, 1.0], "d": 8, "bits": 0}
    cb_mod._CODEBOOK_CACHE[(8, 0)] = sentinel

    def _boom(*args, **kwargs):
        raise AssertionError("compute_lloyd_max_codebook should not be called on cache hit")

    monkeypatch.setattr(cb_mod, "compute_lloyd_max_codebook", _boom)
    result = get_codebook(8, 0)
    assert result is sentinel


def test_get_codebook_loads_from_disk_when_present(monkeypatch):
    disk_cb = {
        "centroids": [-0.3, 0.3],
        "boundaries": [-1.0, 0.0, 1.0],
        "mse_per_coord": 0.01,
        "mse_total": 0.08,
        "d": 8,
        "bits": 1,
    }
    os.makedirs(cb_mod._CODEBOOK_DIR, exist_ok=True)
    path = os.path.join(cb_mod._CODEBOOK_DIR, "codebook_d8_b1.json")
    with open(path, "w") as f:
        json.dump(disk_cb, f)

    def _boom(*args, **kwargs):
        raise AssertionError("should load from disk, not recompute")

    monkeypatch.setattr(cb_mod, "compute_lloyd_max_codebook", _boom)
    result = get_codebook(8, 1)
    assert result == disk_cb
    assert cb_mod._CODEBOOK_CACHE[(8, 1)] == disk_cb


def test_get_codebook_computes_and_writes_when_missing(monkeypatch):
    fixed = {
        "centroids": [-0.3, 0.3],
        "boundaries": [-1.0, 0.0, 1.0],
        "mse_per_coord": 0.02,
        "mse_total": 0.16,
        "d": 8,
        "bits": 1,
    }
    calls = []

    def _stub(d, bits):
        calls.append((d, bits))
        return fixed

    monkeypatch.setattr(cb_mod, "compute_lloyd_max_codebook", _stub)
    result = get_codebook(8, 1)
    assert result == fixed
    assert calls == [(8, 1)]
    # written to disk
    path = os.path.join(cb_mod._CODEBOOK_DIR, "codebook_d8_b1.json")
    assert os.path.exists(path)
    with open(path) as f:
        assert json.load(f) == fixed
    # cached in memory
    assert cb_mod._CODEBOOK_CACHE[(8, 1)] == fixed


def test_get_codebook_isolation_fixture_resets_module_globals(tmp_path):
    # The autouse fixture should have cleared the cache and redirected the dir.
    assert cb_mod._CODEBOOK_CACHE == {}
    assert str(tmp_path / "codebooks") == cb_mod._CODEBOOK_DIR


# ── get_codebook_tensors ────────────────────────────────────────────────────


def test_get_codebook_tensors_returns_cpu_tensors_default_dtype():
    bits = 1
    cb_mod._CODEBOOK_CACHE[(8, bits)] = {
        "centroids": [-0.3, 0.3],
        "boundaries": [-1.0, 0.0, 1.0],
        "mse_per_coord": 0.02,
        "mse_total": 0.16,
        "d": 8,
        "bits": bits,
    }
    centroids, boundaries = get_codebook_tensors(8, bits, device=torch.device("cpu"))
    assert isinstance(centroids, torch.Tensor)
    assert isinstance(boundaries, torch.Tensor)
    assert centroids.device.type == "cpu"
    assert boundaries.device.type == "cpu"
    assert centroids.dtype == torch.float32
    assert boundaries.dtype == torch.float32
    assert len(centroids) == 2**bits
    assert len(boundaries) == 2**bits + 1


def test_get_codebook_tensors_propagates_dtype():
    cb_mod._CODEBOOK_CACHE[(8, 1)] = {
        "centroids": [-0.3, 0.3],
        "boundaries": [-1.0, 0.0, 1.0],
        "mse_per_coord": 0.02,
        "mse_total": 0.16,
        "d": 8,
        "bits": 1,
    }
    centroids, boundaries = get_codebook_tensors(
        8, 1, device=torch.device("cpu"), dtype=torch.float64
    )
    assert centroids.dtype == torch.float64
    assert boundaries.dtype == torch.float64
