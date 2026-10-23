"""Tier-0 (fast classify/route) model: one source of truth, off the NPU by default.

Measured 2026-10-23: the XDNA2 NPU holds ONE FLM model; every model change evicts/reloads it
and holds lemond's lock. The cascade's tier 0 (llama3.2-1b-FLM) thrashed the NPU against a
Kaggle worker's FLM models. Tier 0 now defaults to the iGPU GGUF build of the same model and
is overridable via COHEZION_TIER0_MODEL.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from cohezion.config.defaults import DEFAULT_TIER0_MODEL, tier0_model


_OLD_NPU_LITERAL = "llama3.2-1b-FLM"

# Hermetic: nothing here may reach the live router (a chat request for the tier-0 GGUF
# would make :13305 load it). conftest.no_network refuses AND records every connect.
pytestmark = pytest.mark.usefixtures("no_network")


def _omni_tier0_model_id() -> str:
    from cohezion.inference import triune_orchestrator

    seen: list[str] = []

    def _fake_tier(*, model_id: str, **_kw):
        seen.append(model_id)
        return MagicMock(label=f"gaia:{model_id}")

    with patch.object(triune_orchestrator, "build_gaia_llm_tier", side_effect=_fake_tier):
        triune_orchestrator.build_triune_omni_orchestrator()
    return seen[0]


def _world_model_id() -> str:
    from cohezion.compound.lemonade_world_model import FlumeWorldModel

    return FlumeWorldModel(chat_fn=lambda _t: "0.5")._model_id


def _clr_gate_model() -> str:
    from cohezion.compound.clr_quality_gate import CLRQualityGate

    with patch.object(CLRQualityGate, "_init_gaia_client", return_value=None):
        return CLRQualityGate()._model


def _tri_silicon_npu_phase_model() -> str:
    from cohezion.autopoiesis.tri_silicon_engine import TriSiliconAutopoiesisEngine

    return TriSiliconAutopoiesisEngine(cpu_threads=1).npu_model


def _classifier_fast_hint() -> str:
    from cohezion.inference import task_classifier

    return task_classifier._preferred_model("short_categorical", "npu")


_LIVE_SITES = {
    "omni_cascade_tier0": _omni_tier0_model_id,
    "jepa_world_model": _world_model_id,
    "clr_quality_gate": _clr_gate_model,
    "perpetual_loop_npu_phase": _tri_silicon_npu_phase_model,
    "task_classifier_fast_hint": _classifier_fast_hint,
}


def test_default_tier0_is_igpu_gguf(monkeypatch):
    monkeypatch.delenv("COHEZION_TIER0_MODEL", raising=False)
    assert DEFAULT_TIER0_MODEL == "Llama-3.2-1B-Instruct-GGUF"
    assert tier0_model() == "Llama-3.2-1B-Instruct-GGUF"


@pytest.mark.parametrize("site", sorted(_LIVE_SITES))
def test_live_site_defaults_to_tier0_not_npu_literal(site, monkeypatch):
    monkeypatch.delenv("COHEZION_TIER0_MODEL", raising=False)
    got = _LIVE_SITES[site]()
    assert got != _OLD_NPU_LITERAL, f"{site} still reaches the NPU literal by default"
    assert got == "Llama-3.2-1B-Instruct-GGUF"


@pytest.mark.parametrize("site", sorted(_LIVE_SITES))
def test_live_site_honours_env_override(site, monkeypatch):
    monkeypatch.setenv("COHEZION_TIER0_MODEL", "Override-Model-X")
    assert _LIVE_SITES[site]() == "Override-Model-X"


def test_tier0_gguf_keeps_tier0_sampling_temperature():
    from cohezion.inference.model_card_defaults import get_sampling_defaults

    # The FLM tier 0 ran at 0.3; the GGUF id must not silently fall back to 0.7.
    assert get_sampling_defaults("Llama-3.2-1B-Instruct-GGUF").get("temperature") == 0.3


def test_tier0_gguf_is_classified_igpu_and_light():
    from cohezion.compound.oom_guard import (
        HEAVY_THRESHOLD_GB,
        MODEL_FOOTPRINT_GB,
        ComputeTier,
        tier_for_model,
    )

    assert tier_for_model("Llama-3.2-1B-Instruct-GGUF") is ComputeTier.IGPU
    assert MODEL_FOOTPRINT_GB["Llama-3.2-1B-Instruct-GGUF"] < HEAVY_THRESHOLD_GB


def test_inference_products_routing_product_is_tier0():
    from cohezion.data_mesh import inference_products as ip

    assert ip.COMPOUND_LOOP_MODELS[0] == "Llama-3.2-1B-Instruct-GGUF"
    assert _OLD_NPU_LITERAL not in ip.COMPOUND_LOOP_MODELS
    product = ip._build_product(ip.COMPOUND_LOOP_MODELS[0], None)
    assert product is not None


def test_network_guard_blocks_and_records_live_router(no_network):
    import httpx

    with pytest.raises(httpx.ConnectError):
        httpx.get("http://localhost:13305/v1/models", timeout=1.0)
    assert no_network, "guard did not record the attempted connect"
    no_network.clear()  # recorded as expected; clear so teardown passes


def _llamacpp_entry(ctx_size: int) -> dict:
    return {
        "id": "Llama-3.2-1B-Instruct-GGUF",
        "recipe": "llamacpp",
        "recipe_options": {"ctx_size": ctx_size},
        "max_context_window": 131072,
        "size": 0.777,
    }


def test_tier0_gguf_admission_prices_kv_not_weights_only(monkeypatch):
    """A curated small-weights entry must NOT short-circuit KV pricing for the tier-0 GGUF.

    ctx_size=0 reserves the native 131072-token window: 16 L x 8 KV heads x 64 dim x 2 (K,V)
    x 2 B = 32 KiB/token -> 4.0 GB of KV on top of 0.78 GB weights. 10 GB available clears
    weights + buffer (8.78) but not weights + KV + buffer (12.78).
    """
    from cohezion.compound import oom_guard

    monkeypatch.setattr(oom_guard, "_catalog_entry", lambda *_a, **_k: _llamacpp_entry(0))
    risk = oom_guard.check_oom_risk("Llama-3.2-1B-Instruct-GGUF", available_gb=10.0)
    assert risk.reason != "small model — no gate needed"
    assert risk.footprint_gb > 0.78
    assert not risk.safe


def test_tier0_gguf_admission_admits_at_bounded_ctx(monkeypatch):
    from cohezion.compound import oom_guard

    monkeypatch.setattr(oom_guard, "_catalog_entry", lambda *_a, **_k: _llamacpp_entry(4096))
    risk = oom_guard.check_oom_risk("Llama-3.2-1B-Instruct-GGUF", available_gb=10.0)
    assert risk.safe
    assert risk.footprint_gb == pytest.approx(0.78 + 0.125)


# ── Tier-0 context bound (COHEZION_TIER0_CTX, default 4096) ──────────────────────


def test_tier0_ctx_default_and_override(monkeypatch):
    from cohezion.config.defaults import DEFAULT_TIER0_CTX, tier0_ctx

    monkeypatch.delenv("COHEZION_TIER0_CTX", raising=False)
    assert DEFAULT_TIER0_CTX == 4096
    assert tier0_ctx() == 4096
    monkeypatch.setenv("COHEZION_TIER0_CTX", "8192")
    assert tier0_ctx() == 8192


@pytest.mark.parametrize("raw", ["0", "-1", "abc", ""])
def test_tier0_ctx_rejects_unbounded_or_garbage(raw, monkeypatch):
    """0 means 'native window' to lemonade (the N3 OOM hazard) -- never pass it through."""
    from cohezion.config.defaults import tier0_ctx

    monkeypatch.setenv("COHEZION_TIER0_CTX", raw)
    assert tier0_ctx() == 4096


def test_tier0_ctx_clamped_to_bounded_ceiling(monkeypatch):
    from cohezion.config.defaults import tier0_ctx

    monkeypatch.setenv("COHEZION_TIER0_CTX", "262144")
    assert tier0_ctx() == 32768


def test_omni_cascade_pins_ctx_on_tier0_only(monkeypatch):
    from cohezion.inference import triune_orchestrator

    monkeypatch.setenv("COHEZION_TIER0_CTX", "6144")
    calls: list[dict] = []

    def _fake_tier(**kw):
        calls.append(kw)
        return MagicMock(label=f"gaia:{kw['model_id']}")

    with patch.object(triune_orchestrator, "build_gaia_llm_tier", side_effect=_fake_tier):
        triune_orchestrator.build_triune_omni_orchestrator()
    assert calls[0]["ctx_size"] == 6144
    assert all(c.get("ctx_size") is None for c in calls[1:]), "only tier 0 is pinned"


def test_gaia_tier_passes_ctx_to_client_load_path():
    """GAIA's LemonadeClient issues the /api/v1/load itself; ctx_size_override is how a
    client pins that load. Without it, an unregistered GGUF loads at GAIA's 32768 floor."""
    from cohezion.inference.gaia_adapter import build_gaia_llm_tier

    with patch("gaia.llm.lemonade_client.LemonadeClient") as client_cls:
        build_gaia_llm_tier(model_id="Llama-3.2-1B-Instruct-GGUF", ctx_size=4096)
        assert client_cls.call_args.kwargs["ctx_size_override"] == 4096
        client_cls.reset_mock()
        build_gaia_llm_tier(model_id="Gemma-4-E4B-it-GGUF")
        assert "ctx_size_override" not in client_cls.call_args.kwargs


def test_local_router_fallback_accepts_ctx_pin():
    from cohezion.inference.gaia_adapter import _LocalRouterClient

    _LocalRouterClient(base_url="http://x/api/v1", model="m", ctx_size_override=4096)


def test_clr_gate_pins_tier0_ctx_on_its_gaia_client(monkeypatch):
    from cohezion.compound.clr_quality_gate import CLRQualityGate

    monkeypatch.delenv("COHEZION_TIER0_CTX", raising=False)
    with patch("gaia.llm.lemonade_client.LemonadeClient") as client_cls:
        CLRQualityGate()
        assert client_cls.call_args.kwargs["ctx_size_override"] == 4096
        client_cls.reset_mock()
        CLRQualityGate(model="Gemma-4-E4B-it-GGUF")  # not the tier-0 lane: never re-pinned
        assert "ctx_size_override" not in client_cls.call_args.kwargs


def test_world_model_lazy_client_pins_tier0_ctx(monkeypatch):
    from cohezion.compound.lemonade_world_model import FlumeWorldModel

    monkeypatch.delenv("COHEZION_TIER0_CTX", raising=False)
    with patch("gaia.llm.lemonade_client.LemonadeClient") as client_cls:
        client_cls.return_value.chat_completions.return_value = {
            "choices": [{"message": {"content": "0.5"}}]
        }
        FlumeWorldModel()._chat("x")
        assert client_cls.call_args.kwargs["ctx_size_override"] == 4096


def test_base_recipe_bounds_tier0_ctx():
    """Raw-HTTP tier-0 callers (tri_silicon, router auto-load) cannot carry ctx in a chat
    request; the bound reaches them through the saved recipe (scripts/apply_lemonade_recipes.py)."""
    from cohezion.compound.lemonade_recipes import BASE_RECIPES

    assert BASE_RECIPES["Llama-3.2-1B-Instruct-GGUF"]["ctx_size"] == 4096
