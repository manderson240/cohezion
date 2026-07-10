"""Guard: the omni triune cascade must span THREE distinct compute lanes.

2026-07-09 bug: the CPU tier used Gemma-4-31B, which the router places on
Vulkan (iGPU) — a fake CPU tier that put two of the three tiers on the same
device (and was too slow). The fix routes the CPU tier to Gemma-4-E2B loaded
with llamacpp_backend=cpu. This test fails if any two tiers collapse onto the
same model (the shape of the original bug).
"""

from cohezion.inference.triune_orchestrator import build_triune_omni_orchestrator


def _tier_models(orch):
    return [getattr(getattr(t, "agent", None), "_model", None) for t, _gate in orch.tiers]


def test_three_tiers_are_three_distinct_models():
    orch = build_triune_omni_orchestrator()
    models = _tier_models(orch)
    assert len(models) == 3
    assert len(set(models)) == 3, f"tiers collapsed onto <3 models: {models}"


def test_cpu_tier_is_the_cpu_backend_model_not_a_vulkan_31b():
    orch = build_triune_omni_orchestrator()
    npu, igpu, cpu = _tier_models(orch)
    assert npu == "llama3.2-1b-FLM"          # XDNA2 NPU
    assert igpu == "Gemma-4-E4B-it-GGUF"     # RDNA3.5 iGPU
    assert cpu == "Gemma-4-E2B-it-GGUF"      # Zen5 CPU (llamacpp_backend=cpu)
    # The regression: a 31B here lands on Vulkan → fake CPU tier
    assert "31B" not in cpu
