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
