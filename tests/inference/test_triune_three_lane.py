"""Guard: no two omni triune tiers may be the same configuration, and none may be a CPU GGUF.

2026-07-09 bug: the CPU tier used Gemma-4-31B, which the router placed on Vulkan, so two of
the three tiers collapsed onto one device. 2026-10-21: the tiers moved to FLM (NPU). A
CPU-backend GGUF is charged to lemond's cgroup and a large one throttled every model past
memory.high (GEMS LESSONS 22). Tiers 2 and 3 are deliberately ONE model in its two card
modes, so the invariant is "distinct (model, thinking mode)", not "distinct model".
"""

from cohezion.inference.triune_orchestrator import build_triune_omni_orchestrator


def _tier_configs(orch):
    configs = []
    for tier, _gate in orch.tiers:
        agent = getattr(tier, "agent", None)
        configs.append((agent._model, agent._extra_sampling.get("think")))
    return configs


def test_no_two_tiers_share_a_configuration():
    configs = _tier_configs(build_triune_omni_orchestrator())
    assert len(configs) == 3
    assert len(set(configs)) == 3, f"tiers collapsed onto one configuration: {configs}"


def test_no_tier_is_a_cpu_backend_gguf():
    models = [m for m, _ in _tier_configs(build_triune_omni_orchestrator())]
    assert all(m.endswith("-FLM") for m in models), models
    assert not any("gguf" in m.lower() for m in models), models
