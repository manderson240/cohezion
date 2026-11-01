"""F8: the calibration and diagnostic scripts must not feed a None embedding to np.dot."""

from __future__ import annotations

import asyncio
import importlib.util
import logging
from pathlib import Path

import numpy as np
import pytest

from cohezion.flume.canonical_latent import TextLatentUnavailable


SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"


def _load(rel: str):
    spec = importlib.util.spec_from_file_location(Path(rel).stem, SCRIPTS / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class _NoLatentCache:
    """Cache with one L2 entry whose encoder reports the latent unavailable."""

    def __init__(self, *a, **k):
        self._l2_matrix = np.ones((1, 4), dtype=np.float32)
        self._l2_keys = ["k"]
        self.l2_cache = {}

    def _text_to_embedding(self, text):
        return None


def test_calibration_refuses_to_sweep_without_a_latent(monkeypatch):
    mod = _load("calibration/run_cache_calibration.py")
    monkeypatch.setattr(mod, "SemanticCache", _NoLatentCache)
    with pytest.raises(TextLatentUnavailable):
        asyncio.run(
            mod.evaluate_cache_threshold(
                [{"prompt": "p" * 60, "response": "r"}], {"similarity_threshold": 0.8}
            )
        )


def test_semantic_discrimination_diagnostic_reports_and_returns_without_a_latent(
    monkeypatch, caplog
):
    mod = _load("phase2_vae_diagnostic.py")
    monkeypatch.setattr(mod, "SemanticCache", _NoLatentCache)
    monkeypatch.setattr(mod, "get_encoder", lambda: None)
    with caplog.at_level(logging.ERROR):
        mod.diagnostic_semantic_discrimination()
    assert "text latent unavailable" in caplog.text


class _NoEncoder:
    """The real cold state: an encoder object whose latent is unavailable."""

    def encode_or_none(self, text, strict_window=False):
        return None


def _cold_calibration(monkeypatch, tmp_path):
    """Load the real script with the REAL SemanticCache but no encoder (nothing faked in the cache)."""
    import cohezion.cache.semantic_cache as sc

    monkeypatch.setattr(sc, "get_encoder", lambda: _NoEncoder())
    monkeypatch.setenv("HOME", str(tmp_path))
    return _load("calibration/run_cache_calibration.py")


SAMPLES = [{"prompt": f"prompt number {i} " * 6, "response": f"answer {i}"} for i in range(4)]


def test_calibration_evaluate_refuses_when_l2_stays_empty_cold(monkeypatch, tmp_path):
    mod = _cold_calibration(monkeypatch, tmp_path)
    with pytest.raises(TextLatentUnavailable):
        asyncio.run(mod.evaluate_cache_threshold(SAMPLES, {"similarity_threshold": 0.4}))


def test_calibration_main_cold_saves_no_profile(monkeypatch, tmp_path):
    """Real main(), real SemanticCache, no encoder: must exit nonzero and save nothing."""
    mod = _cold_calibration(monkeypatch, tmp_path)
    saved = []
    monkeypatch.setattr(mod, "load_local_logs", lambda min_len=0: iter(SAMPLES))
    monkeypatch.setattr(mod, "save_calibration_profile", lambda *a, **k: saved.append(a))
    real_sweep = mod.run_parameter_sweep

    async def sweep_no_ram_gate(samples, fn, grid, min_ram_mb=0):
        return await real_sweep(samples, fn, grid, min_ram_mb=0)

    monkeypatch.setattr(mod, "run_parameter_sweep", sweep_no_ram_gate)
    with pytest.raises(SystemExit) as exc:
        asyncio.run(mod.main())
    assert exc.value.code == 1
    assert saved == []


def test_calibration_main_never_saves_when_no_threshold_is_valid(monkeypatch, tmp_path):
    """Probe passes but every candidate errors (e.g. L2 stays empty): still nothing is saved."""
    mod = _cold_calibration(monkeypatch, tmp_path)
    saved = []
    monkeypatch.setattr(mod.SemanticCache, "_text_to_embedding", staticmethod(lambda t: object()))
    monkeypatch.setattr(mod, "load_local_logs", lambda min_len=0: iter(SAMPLES))
    monkeypatch.setattr(mod, "save_calibration_profile", lambda *a, **k: saved.append(a))
    real_sweep = mod.run_parameter_sweep

    async def sweep_no_ram_gate(samples, fn, grid, min_ram_mb=0):
        return await real_sweep(samples, fn, grid, min_ram_mb=0)

    async def zero_hits(samples, cand):
        return {
            "total_lookups": 4,
            "hits": 0,
            "valid_hits": 0,
            "collisions": 0,
            "hit_rate_pct": 0.0,
            "collision_rate_pct": 0.0,
            "valid_hit_rate_pct": 0.0,
        }

    monkeypatch.setattr(mod, "run_parameter_sweep", sweep_no_ram_gate)
    monkeypatch.setattr(mod, "evaluate_cache_threshold", zero_hits)
    with pytest.raises(SystemExit):
        asyncio.run(mod.main())
    assert saved == []
