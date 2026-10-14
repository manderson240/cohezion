"""Unit tests for Hardware Aperture Guard and NPU/CPU local inference policy."""

from __future__ import annotations

import pytest

from cohezion.inference.aperture_guard import (
    AperturePolicyViolation,
    assert_safe_tier1,
    validate_tier1_request,
)
from cohezion.inference.unified_hybrid_router import UnifiedHybridRouter


def test_npu_models_allowed_in_tier1() -> None:
    assert validate_tier1_request("qwen3.5-4b-FLM") == "allow"
    assert validate_tier1_request("qwen3vl-it-4b-FLM") == "allow"
    assert validate_tier1_request("embed-gemma-300m-FLM") == "allow"
    assert validate_tier1_request("custom-model-FLM") == "allow"


def test_lightweight_cpu_models_allowed_in_tier1() -> None:
    assert validate_tier1_request("Qwen3-0.6B-GGUF", backend="cpu", estimated_bytes=500_000_000) == "allow"


def test_vulkan_and_rocm_backends_blocked_in_tier1() -> None:
    assert validate_tier1_request("Qwen3.6-35B-A3B-MTP-GGUF", backend="vulkan") == "reroute_tier2"
    assert validate_tier1_request("Gemma-4-31B-it-GGUF", backend="rocm") == "reroute_tier2"
    assert validate_tier1_request("Qwen3-Coder-30B", backend="vllm") == "reroute_tier2"


def test_large_models_rerouted_to_tier2() -> None:
    assert validate_tier1_request("Qwen3.6-35B-A3B-GGUF") == "reroute_tier2"
    assert validate_tier1_request("Gemma-4-31B-it-GGUF") == "reroute_tier2"
    assert validate_tier1_request("Qwen3-Coder-30B-A3B-Instruct-GGUF") == "reroute_tier2"


def test_assert_safe_tier1_raises_violation() -> None:
    with pytest.raises(AperturePolicyViolation, match="Hardware Aperture Guard blocked"):
        assert_safe_tier1("Qwen3.6-35B-A3B-MTP-GGUF", backend="vulkan")


def test_router_escalates_coding_to_tier2() -> None:
    router = UnifiedHybridRouter()
    res = router.route(task_type="coding", task_importance=0.8)
    assert res.selected_tier == 2
    assert "cloud" in res.model_name or "claude" in res.model_name


def test_router_escalates_deep_reasoning_to_tier2() -> None:
    router = UnifiedHybridRouter()
    res = router.route(task_type="deep_reasoning", task_importance=0.9)
    assert res.selected_tier == 2
    assert "cloud" in res.model_name
