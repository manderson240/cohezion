"""Discriminating tests for the opt-in energy-aware tie-break (2026-06-06, item 6).

Behavior-change item: it ships DEFAULT-OFF (live routing byte-unchanged) and is proven on
the flag-on path. Each test fails a plausible wrong impl:
  - a default that is ON (would change live routing — the 24 router tests would shift),
  - a tie-break that ignores energy (NPU would not win at equal quality),
  - a tie-break that lets energy OVERRIDE quality (a higher-quality CPU model would lose),
  - the "1b" substring collision (mis-rating the 31B CPU model as the 1B NPU model).
"""
from __future__ import annotations

from cohezion.swarm.cost_aware_router import CostAwareRouter


def test_tiebreak_is_default_off() -> None:
    assert CostAwareRouter().energy_aware_tiebreak is False  # non-destructive default


def test_lane_energy_ordering_no_substring_collision() -> None:
    r = CostAwareRouter()
    npu = r._lane_energy_estimate("llama3.2-1b-FLM")
    igpu = r._lane_energy_estimate("Gemma-4-E4B-it-GGUF")
    cpu = r._lane_energy_estimate("Gemma-4-31B-it-GGUF")  # "31b" must NOT match the "1b"/NPU lane
    assert npu < igpu < cpu


def test_pick_prefers_lower_wattage_at_equal_quality() -> None:
    r = CostAwareRouter()
    r.MODEL_QUALITY = {"llama3.2-1b-FLM": 0.8, "Gemma-4-31B-it-GGUF": 0.8}  # equal quality
    # NPU (4 J) beats CPU (55 J) when quality ties.
    assert r._energy_aware_pick(["Gemma-4-31B-it-GGUF", "llama3.2-1b-FLM"]) == "llama3.2-1b-FLM"


def test_pick_quality_dominates_energy() -> None:
    r = CostAwareRouter()
    r.MODEL_QUALITY = {"llama3.2-1b-FLM": 0.5, "Gemma-4-31B-it-GGUF": 0.9}
    # Higher-quality CPU model wins despite higher wattage — energy must NOT override quality.
    assert r._energy_aware_pick(["llama3.2-1b-FLM", "Gemma-4-31B-it-GGUF"]) == "Gemma-4-31B-it-GGUF"


def test_pick_single_candidate_is_identity() -> None:
    r = CostAwareRouter()
    assert r._energy_aware_pick(["only-model"]) == "only-model"
