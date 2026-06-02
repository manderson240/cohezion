"""Registry structure and lookup tests."""

from __future__ import annotations

from cohezion.inference.registry import (
    FleetRegistry,
    Lane,
    ModelEntry,
    Task,
    get_registry,
)


def test_default_registry_has_four_gemma_lanes() -> None:
    registry = FleetRegistry()
    gemma_models = [m for m in registry.models.values() if m.model_id.startswith("Gemma-4-")]
    assert len(gemma_models) == 4, "Expect E2B, E4B, 26B-A4B, 31B per Symphony Guide"


def test_gemma_lanes_bind_to_correct_silicon() -> None:
    registry = FleetRegistry()
    assert registry.models["Gemma-4-E2B-it-GGUF"].lane == Lane.NPU
    assert registry.models["Gemma-4-E4B-it-GGUF"].lane == Lane.IGPU_ROCWMMA
    assert registry.models["Gemma-4-26B-A4B-it-GGUF"].lane == Lane.IGPU_UNIFIED
    assert registry.models["Gemma-4-31B-it-GGUF"].lane == Lane.CPU


def test_gemma_lane_ports_match_symphony_launch_script() -> None:
    registry = FleetRegistry()
    assert "13306" in registry.models["Gemma-4-E2B-it-GGUF"].endpoint
    assert "13307" in registry.models["Gemma-4-E4B-it-GGUF"].endpoint
    assert "13308" in registry.models["Gemma-4-26B-A4B-it-GGUF"].endpoint
    assert "13309" in registry.models["Gemma-4-31B-it-GGUF"].endpoint


def test_for_task_returns_sorted_by_priority() -> None:
    registry = FleetRegistry()
    candidates = registry.for_task(Task.REASONING)
    priorities = [c.priority for c in candidates]
    assert priorities == sorted(priorities), "for_task must yield priority-ordered list"


def test_for_task_returns_only_task_affine_models() -> None:
    registry = FleetRegistry()
    candidates = registry.for_task(Task.CODE_GEN)
    for c in candidates:
        assert Task.CODE_GEN in c.task_affinity


def test_claude_tier_has_ascending_cost() -> None:
    registry = FleetRegistry()
    haiku = registry.models["claude-haiku-4-5"]
    sonnet = registry.models["claude-sonnet-4-6"]
    opus = registry.models["claude-opus-4-7"]
    assert (
        haiku.cost_per_1k_output_usd < sonnet.cost_per_1k_output_usd < opus.cost_per_1k_output_usd
    )


def test_local_only_excludes_cloud() -> None:
    registry = FleetRegistry()
    for m in registry.local_only():
        assert m.lane not in {Lane.CLOUD_OLLAMA, Lane.CLOUD_CLAUDE}


def test_mark_verified_sets_timestamp() -> None:
    registry = FleetRegistry()
    model_id = "Gemma-4-E2B-it-GGUF"
    assert registry.models[model_id].last_verified_at is None
    registry.mark_verified(model_id)
    assert registry.models[model_id].verified_working
    assert registry.models[model_id].last_verified_at is not None


def test_get_registry_returns_singleton() -> None:
    a = get_registry()
    b = get_registry()
    assert a is b


def test_model_entry_is_dataclass_with_expected_fields() -> None:
    from cohezion.inference.registry import WeightQuant

    sample = ModelEntry(
        model_id="x",
        lane=Lane.NPU,
        endpoint="http://localhost:1",
        runtime_backend="flm",
        task_affinity=frozenset({Task.ROUTING}),
        weight_quant=WeightQuant.INT4,
        context_window=1024,
    )
    assert sample.cost_per_1k_input_usd == 0.0
    assert sample.verified_working is False


# Supported values for llama.cpp's --cache-type-k / --cache-type-v flags.
# This set is intentionally narrow — any kv_quant.runtime_flag["llama.cpp"]
# value that isn't in here would be silently ignored at server startup and
# the cache would silently fall back to fp16. Kept as a regression guard
# against the TurboQuant lesson (`turbo3` was declared but the binary had no
# such flag, so the entire declaration was a silent no-op).
LLAMACPP_CACHE_TYPE_WHITELIST = {
    "f32",
    "f16",
    "bf16",
    "q8_0",
    "q4_0",
    "q4_1",
    "q5_0",
    "q5_1",
    "iq4_nl",
}


def test_kv_quant_llamacpp_runtime_flags_are_in_whitelist() -> None:
    registry = FleetRegistry()
    for model in registry.models.values():
        flag = model.kv_quant.runtime_flag.get("llama.cpp")
        if flag is None:
            continue
        assert flag in LLAMACPP_CACHE_TYPE_WHITELIST, (
            f"{model.model_id} declares kv_quant.runtime_flag['llama.cpp']={flag!r} "
            f"but llama-server --cache-type-k/-v only accepts "
            f"{sorted(LLAMACPP_CACHE_TYPE_WHITELIST)}. A value outside the whitelist "
            f"is silently ignored at server startup — the KV cache falls back to fp16 "
            f"with no error. See ~/.claude/plans/do-we-have-turbo-distributed-torvalds.md."
        )


def test_audit_liveness_classifies_all_four_drift_categories() -> None:
    """audit_liveness must reconcile static `verified_working` flags against a
    live probe and classify each local-lane model into exactly one category.

    Uses an injected fake `check_fleet_fn` so this runs deterministically in CI
    without depending on actual Lemonade/Ollama processes.
    """
    from types import SimpleNamespace

    from cohezion.inference.registry import LivenessAudit

    # Fake FleetHealth: npu DOWN, igpu_rocwmma UP, igpu_unified DOWN, cpu UP.
    fake_lanes = {
        "npu": SimpleNamespace(status=SimpleNamespace(value="down")),
        "igpu_rocwmma": SimpleNamespace(status=SimpleNamespace(value="up")),
        "igpu_unified": SimpleNamespace(status=SimpleNamespace(value="down")),
        "cpu": SimpleNamespace(status=SimpleNamespace(value="up")),
    }
    fake_health = SimpleNamespace(lanes=fake_lanes)

    registry = FleetRegistry()
    # Force a known shape: toggle verified_working so all four categories appear.
    registry.models["Gemma-4-E2B-it-GGUF"].verified_working = True  # NPU down → critical_stale
    registry.models["Gemma-4-E4B-it-GGUF"].verified_working = False  # rocwmma up → unverified_up
    registry.models["Gemma-4-26B-A4B-it-GGUF"].verified_working = False  # unified down → lane_down
    registry.models["Gemma-4-31B-it-GGUF"].verified_working = True  # cpu up → healthy

    audit = registry.audit_liveness(check_fleet_fn=lambda: fake_health)

    assert isinstance(audit, LivenessAudit)
    categories = {i.model_id: i.category for i in audit.items}
    assert categories["Gemma-4-E2B-it-GGUF"] == "critical_stale"
    assert categories["Gemma-4-E4B-it-GGUF"] == "unverified_up"
    assert categories["Gemma-4-26B-A4B-it-GGUF"] == "lane_down"
    assert categories["Gemma-4-31B-it-GGUF"] == "healthy"

    # Convenience properties return filtered subsets.
    assert {i.model_id for i in audit.critical_stale} >= {"Gemma-4-E2B-it-GGUF"}
    assert {i.model_id for i in audit.healthy} >= {"Gemma-4-31B-it-GGUF"}
    assert {i.model_id for i in audit.unverified_up} >= {"Gemma-4-E4B-it-GGUF"}
    assert {i.model_id for i in audit.lane_down} >= {"Gemma-4-26B-A4B-it-GGUF"}


def test_audit_liveness_skips_cloud_and_cli_lanes() -> None:
    """Cloud/CLI lanes (Claude, Gemini, Ollama-cloud) have unreachability handled
    via try/except on dispatch, not health probes. audit_liveness should include
    only the four local silicon lanes (NPU/iGPU-ROCWMMA/iGPU-Unified/CPU).
    """
    from types import SimpleNamespace

    fake_health = SimpleNamespace(
        lanes={
            "npu": SimpleNamespace(status=SimpleNamespace(value="up")),
            "igpu_rocwmma": SimpleNamespace(status=SimpleNamespace(value="up")),
            "igpu_unified": SimpleNamespace(status=SimpleNamespace(value="up")),
            "cpu": SimpleNamespace(status=SimpleNamespace(value="up")),
        }
    )
    registry = FleetRegistry()
    audit = registry.audit_liveness(check_fleet_fn=lambda: fake_health)
    local_lane_values = {"npu", "igpu_rocwmma", "igpu_unified", "cpu"}
    for item in audit.items:
        assert item.lane in local_lane_values, (
            f"{item.model_id} got audited with non-local lane {item.lane!r}; "
            "cloud/CLI models should be filtered out."
        )


# --- JetBrains Mellum FIM code-completion specialist ---

_MELLUM_ID = "Mellum-4b-base-gguf-mellum-4b-base.Q8_0.gguf"


def test_mellum_entry_registered_as_code_completion_specialist() -> None:
    """Mellum-4b is present, an iGPU CODE_GEN model served by llama.cpp."""
    registry = FleetRegistry()
    assert _MELLUM_ID in registry.models, "Mellum-4b must be registered"
    e = registry.models[_MELLUM_ID]
    assert e.lane == Lane.IGPU_ROCWMMA
    assert e.task_affinity == frozenset({Task.CODE_GEN})
    assert e.runtime_backend == "llamacpp_hip"
    assert e.endpoint == "http://localhost:13305"
    assert e.reasoning_mode is False  # base FIM model is content-clean


def test_mellum_preferred_over_heavy_coder_for_code_gen() -> None:
    """Fast FIM completion (Mellum) ranks ahead of the heavy qwen3-coder for CODE_GEN."""
    registry = FleetRegistry()
    order = [m.model_id for m in registry.for_task(Task.CODE_GEN)]
    assert _MELLUM_ID in order
    assert order.index(_MELLUM_ID) < order.index("qwen3-coder:30b")
