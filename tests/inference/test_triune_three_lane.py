"""Guard: the omni triune cascade never runs the SAME model id twice.

2026-07-09 bug: the CPU tier used Gemma-4-31B, which the router places on Vulkan (iGPU) -- a
fake CPU tier that put two tiers on one device. 2026-10-23: the tier-0 default became
Gemma-4-E2B-it-GGUF (capability sweep), which was also the legacy tier-2 id. Lemonade keeps
one instance and one saved option set per id, so tiers 0 and 2 collapsed onto one model and
tier 2 became a TRUST-gated resample of tier 0, not a more capable tier.

Fix: tier 2 is configurable (COHEZION_TIER2_MODEL) and tiers are DEDUPLICATED by model id,
first occurrence wins, so the default cascade is [Gemma-4-E2B, Gemma-4-E4B] until a measured
more-capable tier 2 is chosen (pending the large-model sweep). The last surviving tier keeps
the TRUST gate so a cascade always completes.
"""

import pytest

from cohezion.inference.orchestrator import QualityGate
from cohezion.inference.triune_orchestrator import build_triune_omni_orchestrator


# no_network: building the cascade must not touch the live router (refused AND recorded).
pytestmark = pytest.mark.usefixtures("_clean_tier_env", "no_network")

_E2B = "Gemma-4-E2B-it-GGUF"
_E4B = "Gemma-4-E4B-it-GGUF"


@pytest.fixture
def _clean_tier_env(monkeypatch):
    monkeypatch.delenv("COHEZION_TIER0_MODEL", raising=False)
    monkeypatch.delenv("COHEZION_TIER2_MODEL", raising=False)


def _tier_models(orch):
    return [getattr(getattr(t, "agent", None), "_model", None) for t, _gate in orch.tiers]


def test_default_cascade_is_deduplicated_to_e2b_then_e4b():
    models = _tier_models(build_triune_omni_orchestrator())
    assert models == [_E2B, _E4B], models


def test_tiers_are_never_duplicated_by_model_id():
    models = _tier_models(build_triune_omni_orchestrator())
    assert len(set(models)) == len(models), f"duplicate tier model ids: {models}"


def test_last_tier_is_trust_gated_so_the_cascade_completes():
    orch = build_triune_omni_orchestrator()
    assert orch.tiers[-1][1] is QualityGate.TRUST
    assert all(g is not QualityGate.TRUST for _t, g in orch.tiers[:-1])


def test_tier2_env_adds_a_third_distinct_tier(monkeypatch):
    monkeypatch.setenv("COHEZION_TIER2_MODEL", "Qwen3-8B-GGUF")
    orch = build_triune_omni_orchestrator()
    assert _tier_models(orch) == [_E2B, _E4B, "Qwen3-8B-GGUF"]
    assert orch.tiers[-1][1] is QualityGate.TRUST
    assert orch.tiers[1][1] is not QualityGate.TRUST  # E4B keeps its escalation gate


def test_tier2_equal_to_tier0_is_deduplicated(monkeypatch):
    monkeypatch.setenv("COHEZION_TIER2_MODEL", _E2B)
    assert _tier_models(build_triune_omni_orchestrator()) == [_E2B, _E4B]


def test_tier0_equal_to_tier1_keeps_first_occurrence(monkeypatch):
    monkeypatch.setenv("COHEZION_TIER0_MODEL", _E4B)
    models = _tier_models(build_triune_omni_orchestrator())
    assert models == [_E4B, _E2B], models


def test_tier0_override_restores_three_distinct_models(monkeypatch):
    monkeypatch.setenv("COHEZION_TIER0_MODEL", "Llama-3.2-1B-Instruct-GGUF")
    models = _tier_models(build_triune_omni_orchestrator())
    assert models == ["Llama-3.2-1B-Instruct-GGUF", _E4B, _E2B], models


def test_no_tier_is_a_vulkan_31b():
    # The 2026-07-09 regression: a 31B here lands on Vulkan -> fake CPU tier.
    assert not any("31B" in m for m in _tier_models(build_triune_omni_orchestrator()))
