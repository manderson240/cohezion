"""Tier-0 (fast classify/route) model: one source of truth, NPU-first.

The XDNA2 NPU holds ONE FLM model; every model change evicts/reloads it under lemond's lock,
so tier 0 is the single shared NPU model. User directive 2026-10-23/24: NPU unless a task
needs an iGPU-only model. Calibrated gauntlet (n=39): gemma4-it-e2b-FLM think=false 1.000,
Gemma-4-E2B-it-GGUF 0.973, llama3.2-1b-FLM 0.513. The GGUF and Llama-1B GGUF stay available
as COHEZION_TIER0_MODEL overrides.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from cohezion.config.defaults import DEFAULT_TIER0_MODEL, tier0_model


_OLD_NPU_LITERAL = "llama3.2-1b-FLM"
_TIER0 = "gemma4-it-e2b-FLM"
_GGUF = "Gemma-4-E2B-it-GGUF"  # the 2026-10-23 default, now an opt-in override

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


def test_default_tier0_is_gemma4_e2b_flm(monkeypatch):
    monkeypatch.delenv("COHEZION_TIER0_MODEL", raising=False)
    assert DEFAULT_TIER0_MODEL == _TIER0
    assert tier0_model() == _TIER0


@pytest.mark.parametrize("site", sorted(_LIVE_SITES))
def test_live_site_defaults_to_tier0_not_npu_literal(site, monkeypatch):
    monkeypatch.delenv("COHEZION_TIER0_MODEL", raising=False)
    got = _LIVE_SITES[site]()
    assert got != _OLD_NPU_LITERAL, f"{site} still reaches the NPU literal by default"
    assert got == _TIER0


@pytest.mark.parametrize("site", sorted(_LIVE_SITES))
def test_live_site_honours_env_override(site, monkeypatch):
    monkeypatch.setenv("COHEZION_TIER0_MODEL", "Override-Model-X")
    assert _LIVE_SITES[site]() == "Override-Model-X"


def test_opt_in_llama_tier0_keeps_tier0_sampling_temperature():
    from cohezion.inference.model_card_defaults import get_sampling_defaults

    # The FLM tier 0 ran at 0.3; the GGUF id must not silently fall back to 0.7.
    assert get_sampling_defaults("Llama-3.2-1B-Instruct-GGUF").get("temperature") == 0.3


def test_default_tier0_uses_gemma4_card_sampling():
    """E2B's GGUF general.sampling is temp 1.0 / top_p 0.95 / top_k 64; the request layer
    must send the same card values, never the 0.7 unknown-model fallback or greedy 0.0."""
    from cohezion.inference.model_card_defaults import get_sampling_defaults

    assert get_sampling_defaults(_GGUF) == {"temperature": 1.0, "top_k": 64, "top_p": 0.95}


def test_gguf_override_gets_reasoning_format_none_and_flm_default_does_not():
    """FLM has no reasoning_content channel; reasoning_format is a llama.cpp-only field."""
    from cohezion.inference.gaia_adapter import _is_llamacpp_thinking_model

    assert _is_llamacpp_thinking_model(_GGUF)
    assert not _is_llamacpp_thinking_model(_TIER0)


def test_default_tier0_is_classified_npu_with_measured_weight():
    from cohezion.compound.oom_guard import MODEL_FOOTPRINT_GB, ComputeTier, tier_for_model

    assert tier_for_model(_TIER0) is ComputeTier.NPU
    assert MODEL_FOOTPRINT_GB[_TIER0] == 6.4  # measured flm-real RSS at the saved ctx 32768


def test_gguf_override_is_classified_igpu_and_light():
    from cohezion.compound.oom_guard import (
        HEAVY_THRESHOLD_GB,
        MODEL_FOOTPRINT_GB,
        ComputeTier,
        tier_for_model,
    )

    assert tier_for_model(_GGUF) is ComputeTier.IGPU
    assert MODEL_FOOTPRINT_GB[_GGUF] < HEAVY_THRESHOLD_GB


def test_default_tier0_flm_admission_is_not_kv_priced(monkeypatch):
    """The flm recipe is not a llama.cpp full-ctx KV reservation: the admission gate prices
    the curated 6.0 GB weight and no KV, even at the 131072 native window."""
    from cohezion.compound import oom_guard

    entry = {"id": _TIER0, "recipe": "flm", "recipe_options": {}, "size": 6.0}
    monkeypatch.setattr(oom_guard, "_catalog_entry", lambda *_a, **_k: entry)
    risk = oom_guard.check_oom_risk(_TIER0, available_gb=100.0, npu_exempt=False)
    assert risk.safe
    assert risk.footprint_gb == pytest.approx(6.4)


def test_inference_products_routing_product_is_tier0():
    from cohezion.data_mesh import inference_products as ip

    assert ip.COMPOUND_LOOP_MODELS[0] == _TIER0
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


# ── Tier-0 context: ONE authority, the saved recipe (no client-side pins) ─────────
# Consumption test against a recording fake lemonade: test_tier0_single_ctx_authority.py


def test_base_recipe_bounds_tier0_ctx():
    """No caller pins or loads tier 0; the router auto-loads it at this saved recipe ctx
    (written by scripts/apply_lemonade_recipes.py)."""
    from cohezion.compound.lemonade_recipes import BASE_RECIPES

    recipe = BASE_RECIPES[_TIER0]
    # FLM rounds ctx up to a power of two (min 512): 32768 is served as-is.
    assert recipe == {"ctx_size": 32768}, "flm recipe: ctx only, no llama.cpp keys"
    # The opt-in overrides stay bounded too.
    gguf = BASE_RECIPES[_GGUF]
    assert gguf["ctx_size"] == 4096
    assert gguf["llamacpp_backend"] == "auto"  # device probe -> Vulkan iGPU; not "rocm"/"cpu"
    assert gguf["llamacpp_args"].split()[-2:] == ["-np", "1"]
    assert BASE_RECIPES["Llama-3.2-1B-Instruct-GGUF"]["ctx_size"] == 4096


@pytest.mark.parametrize("model", [_TIER0, _GGUF])
def test_ops_manifest_matches_base_recipe_for_tier0(model):
    """Two appliers write lemonade's saved options for the same id: BASE_RECIPES
    (scripts/apply_lemonade_recipes.py) and the ops manifest (scripts/ops/...). Any field
    that differs is re-stamped by whichever ran last -- two ctx/backend authorities. A key
    absent from one side must be absent from the other (the FLM entry has no llamacpp keys)."""
    from pathlib import Path

    import yaml

    from cohezion.compound.lemonade_recipes import BASE_RECIPES

    manifest = Path(__file__).resolve().parents[2] / "scripts/ops/lemonade-recipes.md"
    front = yaml.safe_load(manifest.read_text().split("---", 2)[1])
    entries = [e for e in front["recipes"] if e["model"] == model]
    assert len(entries) == 1, f"{model} must have exactly one ops-manifest entry"
    entry = entries[0]
    keys = ("ctx_size", "llamacpp_backend", "llamacpp_args")
    ops = {k: entry[k] for k in keys if k in entry}
    assert ops == dict(BASE_RECIPES[model])


def _e2b_entry(ctx_size: int) -> dict:
    return {
        "id": _GGUF,
        "recipe": "llamacpp",
        "recipe_options": {"ctx_size": ctx_size},
        "max_context_window": 131072,
        "size": 4.09,
    }


def test_gguf_tier0_kv_rate_is_from_gguf_architecture():
    """15 KV-owning layers (35 - 20 shared): 3 full x 512 + 12 SWA x 256, 1 KV head, f16."""
    from cohezion.compound.oom_guard import KV_KIB_PER_TOKEN

    assert _TIER0 not in KV_KIB_PER_TOKEN  # FLM KV is unmeasured; no GGUF price carried over
    assert KV_KIB_PER_TOKEN[_GGUF] == 2 * 1 * (3 * 512 + 12 * 256) * 2 / 1024 == 18.0


def test_gguf_tier0_admission_prices_kv_not_weights_only(monkeypatch):
    """ctx_size=0 reserves the 131072 native window: 18 KiB x 131072 = 2.25 GB of KV on top of
    4.09 GB weights. 13 GB clears weights + buffer (12.09) but not + KV (14.34)."""
    from cohezion.compound import oom_guard

    monkeypatch.setattr(oom_guard, "_catalog_entry", lambda *_a, **_k: _e2b_entry(0))
    risk = oom_guard.check_oom_risk(_GGUF, available_gb=13.0)
    assert risk.reason != "small model — no gate needed"
    assert risk.footprint_gb == pytest.approx(4.09 + 2.25)
    assert not risk.safe


def test_gguf_tier0_admission_admits_at_bounded_ctx(monkeypatch):
    from cohezion.compound import oom_guard

    monkeypatch.setattr(oom_guard, "_catalog_entry", lambda *_a, **_k: _e2b_entry(4096))
    risk = oom_guard.check_oom_risk(_GGUF, available_gb=13.0)
    assert risk.safe
    assert risk.footprint_gb == pytest.approx(4.09 + 18.0 * 4096 / (1024 * 1024))


def test_router_policy_sends_tier0_class_rules_to_the_shared_npu_model() -> None:
    """The NPU holds one LLM; every tier-0-class router rule must name the shared tier-0 model,
    and no other small FLM chat model may remain a router candidate (each would swap the slot)."""
    import json
    from pathlib import Path

    policy = json.loads(
        (Path(__file__).resolve().parents[2] / "config/router/cohezion-router.json").read_text()
    )
    routing = policy["routing"]
    rules = {rule["id"]: rule["route_to"] for rule in routing["rules"]}
    assert routing["default_model"] == DEFAULT_TIER0_MODEL
    for rule_id in ("fast-qna", "trivial-ack", "default-npu", "reason"):
        assert rules[rule_id] == DEFAULT_TIER0_MODEL, rule_id
    retired = {"llama3.2-1b-FLM", "qwen3-4b-FLM"}
    assert not retired & set(policy["components"])
    assert not retired & set(routing["candidates"])


def test_router_long_context_rule_is_not_shadowed_by_tier0_rules() -> None:
    """The shared tier-0 model has a bounded saved ctx; long-context must route elsewhere.

    Rules are first-match. Any rule sending prompts to the tier-0 model without its own
    max_chars bound must come AFTER the long-context rule, or long prompts that also match it
    (e.g. "analyze this log" + a pasted log) overflow the tier-0 ctx instead."""
    import json
    from pathlib import Path

    policy = json.loads(
        (Path(__file__).resolve().parents[2] / "config/router/cohezion-router.json").read_text()
    )
    rules = policy["routing"]["rules"]
    ids = [rule["id"] for rule in rules]
    long_ctx = ids.index("long-context")
    assert rules[long_ctx]["route_to"] != DEFAULT_TIER0_MODEL

    def bounded(match: dict) -> bool:
        if "max_chars" in match:
            return True
        return any(bounded(m) for m in match.get("all", []))

    for i, rule in enumerate(rules[:long_ctx]):
        if rule["route_to"] == DEFAULT_TIER0_MODEL:
            assert bounded(rule["match"]), f"{rule['id']} shadows long-context unbounded"
