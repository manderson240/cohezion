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
