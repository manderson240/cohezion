"""Gate v2 pricing invariants: KV reservation, name aliases, catalog-zero guard.

Origin (2026-09-01): journal forensics showed `user.Qwen3.6-35B-A3B-ThinkingCoder`
(catalog `ctx_size: 0`) launching with n_ctx_slot=262144 — ~24 GiB KV over 21.7 GB
weights — while the enforcing gate priced the alias at UNKNOWN_ASSUMED_GB (8 GB) and
would ALLOW it at 24 GB available. Two independent under-pricing holes: the `user.`
catalog prefix drops names out of every table, and weights-only pricing ignores the
full-context KV reservation llama.cpp makes at load time.

Every test here is discriminating: it fails on the pre-v2 weights-only implementation.
"""

from __future__ import annotations

import pytest

from cohezion.compound import oom_guard
from cohezion.compound.oom_guard import (
    UNKNOWN_ASSUMED_GB,
    check_oom_risk,
    estimate_kv_gb,
    model_matches_loaded_entry,
    normalize_model_name,
)


def _entry(**over: object) -> dict[str, object]:
    base: dict[str, object] = {
        "id": "Qwen3.6-35B-A3B-ThinkingCoder",
        "size": 21.7,
        "recipe": "llamacpp",
        "max_context_window": 262144,
        "recipe_options": {"ctx_size": 0},
    }
    base.update(over)
    return base


@pytest.fixture()
def catalog(monkeypatch: pytest.MonkeyPatch):
    """Route catalog lookups to an in-test dict; no HTTP."""
    entries: dict[str, dict[str, object]] = {}

    def fake_entry(
        name: str, timeout_s: float = 2.0, base_url: str | None = None
    ) -> dict[str, object] | None:
        return entries.get(normalize_model_name(name))

    monkeypatch.setattr(oom_guard, "_catalog_entry", fake_entry)
    return entries


class TestNormalizeModelName:
    def test_strips_user_prefix(self):
        assert normalize_model_name("user.Qwen3.8-27B-NoThinking") == "Qwen3.8-27B-NoThinking"

    def test_bare_name_unchanged(self):
        assert normalize_model_name("Gemma-4-E4B-it-GGUF") == "Gemma-4-E4B-it-GGUF"

    def test_only_leading_prefix_stripped(self):
        # A name merely CONTAINING "user." must not be mangled.
        assert normalize_model_name("my-user.model") == "my-user.model"


class TestAliasPricing:
    """The user.-prefix bypass: alias must price like the bare name."""

    def test_user_prefixed_curated_model_priced_like_bare(self, catalog):
        bare = check_oom_risk("Qwen3.6-35B-A3B-GGUF", available_gb=24.0, npu_exempt=False)
        aliased = check_oom_risk("user.Qwen3.6-35B-A3B-GGUF", available_gb=24.0, npu_exempt=False)
        # Pre-fix: bare refused (21.7+8 > 24) while the alias sailed through at 8 GB.
        assert bare.safe is False
        assert aliased.safe is False
        assert aliased.footprint_gb == bare.footprint_gb

    def test_alias_matches_loaded_entry_both_directions(self):
        entry: dict[str, object] = {"model_name": "Qwen3.8-27B-NoThinking", "checkpoint": ""}
        assert model_matches_loaded_entry("user.Qwen3.8-27B-NoThinking", entry)
        aliased: dict[str, object] = {
            "model_name": "user.Qwen3.8-27B-NoThinking",
            "checkpoint": "",
        }
        assert model_matches_loaded_entry("Qwen3.8-27B-NoThinking", aliased)


class TestKVReservation:
    """ctx-aware pricing: llama.cpp reserves full-ctx KV at load."""

    def test_ctx_zero_prices_native_context(self, catalog):
        # ctx_size:0 → n_ctx_slot = native max (PROVEN: journal 08-31 14:41:12,
        # n_ctx_slot = 262144). 96 KiB/token × 262144 ≈ 24 GiB KV on top of weights.
        catalog["Qwen3.6-35B-A3B-ThinkingCoder"] = _entry()
        risk = check_oom_risk("Qwen3.6-35B-A3B-ThinkingCoder", available_gb=35.0, npu_exempt=False)
        # Pre-fix: 21.7 weights + 8 buffer = 29.7 < 35 → allowed. v2 must refuse.
        assert risk.safe is False
        assert risk.footprint_gb > 40.0

    def test_explicit_modest_ctx_not_overpriced(self, catalog):
        catalog["Qwen3.6-35B-A3B-GGUF"] = _entry(
            id="Qwen3.6-35B-A3B-GGUF", recipe_options={"ctx_size": 16384}
        )
        risk = check_oom_risk("Qwen3.6-35B-A3B-GGUF", available_gb=35.0, npu_exempt=False)
        # 21.7 + ~1.5 KV + 8 buffer ≈ 31.2 < 35 → must still be allowed.
        assert risk.safe is True
        assert risk.footprint_gb < 26.0

    def test_absent_ctx_clamped_not_native(self, catalog):
        # opts without ctx_size → assume lemond's own unknown-max clamp (32768),
        # NOT the 262144 native window: over-pricing every un-optioned model would
        # refuse loads that launch small.
        catalog["Qwen3.8-27B-GGUF"] = _entry(id="Qwen3.8-27B-GGUF", size=17.2, recipe_options={})
        kv_native = estimate_kv_gb("Qwen3.8-27B-GGUF", 262144, weights_gb=17.2)
        priced = check_oom_risk("Qwen3.8-27B-GGUF", available_gb=200.0, npu_exempt=False)
        assert priced.footprint_gb < 17.2 + kv_native
        assert priced.footprint_gb > 17.2  # but KV is not zero either

    def test_non_llamacpp_recipe_prices_weights_only(self, catalog):
        catalog["qwen3.6-moe-35b-a3b-FLM"] = _entry(
            id="qwen3.6-moe-35b-a3b-FLM",
            size=24.3,
            recipe="flm",
            recipe_options={"ctx_size": 16384},
        )
        risk = check_oom_risk("qwen3.6-moe-35b-a3b-FLM", available_gb=40.0, npu_exempt=False)
        assert risk.footprint_gb == pytest.approx(24.3, abs=0.5)

    def test_estimate_kv_gb_curated_shape(self):
        # Qwen3-MoE GQA: 48 layers × 4 KV heads × 128 head_dim, f16 → 96 KiB/token.
        kv = estimate_kv_gb("Qwen3.6-35B-A3B-GGUF", 262144, weights_gb=21.7)
        assert 20.0 < kv < 28.0

    def test_estimate_kv_gb_scales_linearly_with_ctx(self):
        small = estimate_kv_gb("Qwen3.6-35B-A3B-GGUF", 16384, weights_gb=21.7)
        large = estimate_kv_gb("Qwen3.6-35B-A3B-GGUF", 262144, weights_gb=21.7)
        assert large == pytest.approx(small * 16, rel=0.01)


class TestCatalogZeroGuard:
    def test_catalog_size_zero_falls_back_to_assumed(self, catalog):
        # A router reporting size 0 must not resurrect the 0.0-footprint fail-open.
        catalog["mystery-model"] = _entry(id="mystery-model", size=0.0, recipe_options={})
        risk = check_oom_risk("mystery-model", available_gb=100.0, npu_exempt=False)
        assert risk.footprint_gb >= UNKNOWN_ASSUMED_GB


class TestCatalogEntryMatching:
    """rv-gate-v2 M2: production _catalog_entry must normalize BOTH sides — the live
    catalog itself carries user.-prefixed ids. The `catalog` fixture bypasses the real
    matcher, so this class exercises the REAL _catalog_entry against a fake payload."""

    def _client(self, ids: list[str]):
        payload = {"data": [{"id": i, "size": 21.7, "recipe": "llamacpp"} for i in ids]}

        class _Resp:
            def raise_for_status(self):
                return None

            def json(self):
                return payload

        class _Client:
            def __init__(self, *a, **k):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def get(self, *a, **k):
                return _Resp()

        return _Client

    def test_prefixed_catalog_id_found_by_bare_name(self, monkeypatch):
        monkeypatch.setattr(
            oom_guard.httpx, "Client", self._client(["user.Qwen3.8-27B-NoThinking"])
        )
        entry = oom_guard._catalog_entry("Qwen3.8-27B-NoThinking")
        assert entry is not None and entry["size"] == 21.7

    def test_prefixed_query_finds_bare_catalog_id(self, monkeypatch):
        monkeypatch.setattr(oom_guard.httpx, "Client", self._client(["Qwen3.8-27B-NoThinking"]))
        assert oom_guard._catalog_entry("user.Qwen3.8-27B-NoThinking") is not None


class TestVllmPricing:
    def test_vllm_recipe_priced_as_pool_fraction(self, catalog, monkeypatch):
        # rv-gate-v2 M1: vLLM pre-allocates ~0.9 of the pool at load regardless of ctx.
        # A weights-only price (36 GB) at 46 GB available would ALLOW a load that
        # claims ~110 GB of a 122.8 GB pool.
        monkeypatch.setattr(oom_guard, "_mem_total_gb", lambda: 122.8)
        catalog["Qwen3.6-35B-A3B-FP8-vLLM-lowconc"] = _entry(
            id="Qwen3.6-35B-A3B-FP8-vLLM-lowconc",
            size=36.0,
            recipe="vllm",
            recipe_options={},
        )
        risk = check_oom_risk(
            "Qwen3.6-35B-A3B-FP8-vLLM-lowconc", available_gb=46.0, npu_exempt=False
        )
        assert risk.safe is False
        assert risk.footprint_gb > 100.0
