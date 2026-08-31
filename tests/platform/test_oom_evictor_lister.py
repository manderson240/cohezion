"""Discriminating tests for OOMEvictor's default lister (defect found 2026-07-29).

THE DEFECT: `_default_lister` read `/api/v1/models` — the CATALOG of everything available —
and filtered it by registry membership. Loaded models live at `/api/v1/health` under
`all_models_loaded`. Catalog != loaded, so the lister failed in BOTH directions:

  PHANTOMS  it reported Gemma-4-31B and deepseek-r1-0528-8b-FLM as loaded when they were not
            -> the evictor picks an unloaded victim, "evicts" it, and frees ZERO bytes
  BLIND     it missed 6 of 10 actually-loaded models (Bonsai-8B, Qwen3-0.6B, SD-Turbo,
            Whisper, kokoro, nomic-embed) -> their RAM can never be reclaimed

Measured live: health reported 10 loaded, the lister reported 6, with 2 phantoms.

This was invisible because the module has ZERO production consumers — nothing ever called
`install_oom_evictor()`, so the lister was never exercised against a real server. A dormant
safeguard is not a safeguard; it is an untested claim.

Both tests below FAIL against the catalog-reading implementation.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from cohezion.platform.oom_evictor import LoadedModel, OOMEvictor, _default_lister


class _Resp:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


# health reports 3 loaded; the catalog contains 5. Only the health set is correct.
_HEALTH = {
    "all_models_loaded": [
        {"model_name": "Gemma-4-E4B-it-GGUF"},
        {"model_name": "Qwen3-0.6B-GGUF"},
        {"model_name": "SD-Turbo"},
    ]
}
_CATALOG = {
    "data": [
        {"id": "Gemma-4-E4B-it-GGUF"},
        {"id": "Gemma-4-31B-it-GGUF"},  # in catalog, NOT loaded — the phantom
        {"id": "deepseek-r1-0528-8b-FLM"},  # in catalog, NOT loaded — the phantom
        {"id": "Qwen3-0.6B-GGUF"},
        {"id": "SD-Turbo"},
    ]
}


class _Entry:
    def __init__(self, priority=100, lane="igpu"):
        self.priority = priority
        self.lane = lane


class _Registry:
    # Every id is "managed", so the ONLY thing separating the two implementations is
    # which endpoint they consult — not registry filtering.
    models = {
        mid: _Entry()
        for mid in (
            "Gemma-4-E4B-it-GGUF",
            "Gemma-4-31B-it-GGUF",
            "deepseek-r1-0528-8b-FLM",
            "Qwen3-0.6B-GGUF",
            "SD-Turbo",
        )
    }


def _fake_get(url, timeout=None):
    if "health" in url:
        return _Resp(_HEALTH)
    return _Resp(_CATALOG)


class TestDefaultLister:
    def test_lists_only_actually_loaded_models(self):
        """DISCRIMINATING: the catalog-reading version returns 5 here, including 2 phantoms."""
        with (
            patch("httpx.get", side_effect=_fake_get),
            patch("cohezion.inference.registry.get_registry", return_value=_Registry()),
        ):
            got = {m.model_id for m in _default_lister()}

        assert got == {"Gemma-4-E4B-it-GGUF", "Qwen3-0.6B-GGUF", "SD-Turbo"}
        assert "Gemma-4-31B-it-GGUF" not in got, "phantom: in catalog but not loaded"
        assert "deepseek-r1-0528-8b-FLM" not in got, "phantom: in catalog but not loaded"

    def test_unreachable_server_returns_empty_not_raises(self):
        """Fail-soft: the evictor becomes a no-op rather than guessing."""
        with patch("httpx.get", side_effect=OSError("connection refused")):
            assert _default_lister() == []


class TestEvictorUsesLister:
    def test_evicts_least_preferred_of_the_LOADED_set(self):
        """DISCRIMINATING: a phantom carrying the worst priority would be chosen by the
        broken lister, wasting the eviction on a model that holds no memory."""
        unloaded: list[str] = []

        evictor = OOMEvictor(
            lister=lambda: [
                LoadedModel("Gemma-4-E4B-it-GGUF", priority=10),
                LoadedModel("Qwen3-0.6B-GGUF", priority=90),  # least preferred, IS loaded
            ],
            unloader=lambda mid: (unloaded.append(mid), True)[1],
        )
        ev = evictor.evict_one()

        assert ev is not None and ev.succeeded
        assert unloaded == ["Qwen3-0.6B-GGUF"]

    def test_no_loaded_models_is_a_noop(self):
        evictor = OOMEvictor(lister=lambda: [], unloader=lambda mid: True)
        assert evictor.evict_one() is None


if __name__ == "__main__":
    pytest.main([__file__, "-q"])
