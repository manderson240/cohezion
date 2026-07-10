"""Quarter-on-a-String must dispatch to lane-RESIDENT models (never evict).

2026-07-09: the protocol is 'the quarter always comes back on its string' —
every call runs on local silicon at $0. For that to be REAL (not a spec that
triggers the embed-eviction race, Kanban 32aa143b3962), each complexity must
map to a model resident on one of the three device lanes established by
build_triune_omni_orchestrator, so no dispatch auto-loads/evicts a model.
"""

from cohezion.inference.direct_tier import _QUARTER_MODELS, quarter_on_a_string_tier


# The three device-lane models (NPU / iGPU / CPU) that stay resident.
_LANE_MODELS = {
    "llama3.2-1b-FLM",  # NPU
    "Gemma-4-E4B-it-GGUF",  # iGPU
    "Gemma-4-E2B-it-GGUF",  # CPU
}


def test_every_quarter_model_is_lane_resident():
    stale = {c: m for c, m in _QUARTER_MODELS.items() if m not in _LANE_MODELS}
    assert not stale, f"quarter maps to non-lane-resident models (will evict): {stale}"


def test_all_three_lanes_are_used():
    # routine=NPU, synthesis/orchestration=iGPU, review=CPU — spread across silicon
    assert _QUARTER_MODELS["routine"] == "llama3.2-1b-FLM"
    assert _QUARTER_MODELS["review"] == "Gemma-4-E2B-it-GGUF"  # the CPU lane
    assert set(_QUARTER_MODELS.values()) == _LANE_MODELS


def test_cloud_is_never_referenced():
    # No cloud model names in the quarter map — the quarter never leaves the string.
    joined = " ".join(_QUARTER_MODELS.values()).lower()
    for cloud in ("claude", "gpt", "sonnet", "opus", "gemini", "openai"):
        assert cloud not in joined


def test_tier_reports_zero_cost_and_resolves_card_temperature():
    tier = quarter_on_a_string_tier("synthesis")
    assert tier.model_id == "Gemma-4-E4B-it-GGUF"
    # Gemma card temperature is 1.0, not the generic 0.3 default
    assert tier.temperature == 1.0
