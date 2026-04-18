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
    sample = ModelEntry(
        model_id="x",
        lane=Lane.NPU,
        endpoint="http://localhost:1",
        llamacpp_backend="flm",
        task_affinity=frozenset({Task.ROUTING}),
        quantization="INT4",
        context_window=1024,
    )
    assert sample.cost_per_1k_input_usd == 0.0
    assert sample.verified_working is False
