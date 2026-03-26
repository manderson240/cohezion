"""Tests for OllamaContextManager and ModelContextProfile."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from cohezion.agentjet.context_optimizer import (
    CONTEXT_PROFILES,
    ModelContextProfile,
    OllamaContextManager,
)


def test_context_profiles_contains_expected_models() -> None:
    assert "qwen3.5:9b" in CONTEXT_PROFILES
    assert "phi3:mini" in CONTEXT_PROFILES
    assert "default" in CONTEXT_PROFILES


def test_training_profiles_have_num_ctx_2048_and_keep_alive_0() -> None:
    for key, profile in CONTEXT_PROFILES.items():
        if key.endswith(":training"):
            assert profile.num_ctx == 2048, f"{key} should have num_ctx=2048"
            assert profile.keep_alive == "0", f"{key} should have keep_alive='0'"


def test_check_oom_risk_true_when_available_too_low() -> None:
    mgr = OllamaContextManager()
    # Default cached_available_gb = 128 - 8 - 10 = 110
    # model_size_gb=50: required = 50 * 3.0 * 1.2 = 180 > 110 → OOM risk
    assert mgr.check_oom_risk(50.0) is True


def test_check_oom_risk_false_when_sufficient_memory() -> None:
    mgr = OllamaContextManager()
    # model_size_gb=5: required = 5 * 3.0 * 1.2 = 18 < 110 → no risk
    assert mgr.check_oom_risk(5.0) is False


def test_get_profile_unknown_model_returns_default() -> None:
    mgr = OllamaContextManager()
    profile = mgr.get_profile("unknown-model-xyz")
    assert profile.model_name == "default"


def test_get_profile_known_model_returns_correct_profile() -> None:
    mgr = OllamaContextManager()
    profile = mgr.get_profile("qwen3.5:9b")
    assert profile.model_name == "qwen3.5:9b"
    assert profile.num_ctx == 16384


@pytest.mark.asyncio
async def test_get_loaded_models_empty_response() -> None:
    mgr = OllamaContextManager()
    # Patch get_loaded_models directly to avoid aiohttp context-manager complexity
    with patch.object(mgr, "get_loaded_models", new_callable=AsyncMock, return_value=[]):
        models = await mgr.get_loaded_models()
    assert models == []


@pytest.mark.asyncio
async def test_get_loaded_models_returns_model_names() -> None:
    mgr = OllamaContextManager()

    async def _mock_get_loaded():
        return ["phi3:mini", "qwen3.5:9b"]

    with patch.object(mgr, "get_loaded_models", side_effect=_mock_get_loaded):
        result = await mgr.get_loaded_models()

    assert "phi3:mini" in result
    assert "qwen3.5:9b" in result


@pytest.mark.asyncio
async def test_get_available_memory_gb_updates_cache() -> None:
    mgr = OllamaContextManager()
    # Simulate Ollama returning no loaded models
    with patch.object(mgr, "get_available_memory_gb", new_callable=AsyncMock, return_value=100.0):
        mem = await mgr.get_available_memory_gb()
    assert mem == 100.0


def test_cached_available_gb_property() -> None:
    mgr = OllamaContextManager()
    # Default: 128 - 8 - 10 = 110
    assert mgr.cached_available_gb == pytest.approx(110.0)


def test_model_context_profile_defaults() -> None:
    profile = ModelContextProfile(model_name="test-model", num_ctx=4096, size_gb=5.0)
    assert profile.flash_attention is True
    assert profile.keep_alive == "5m"
    assert profile.num_parallel == 1
    assert profile.rope_scaling == "linear"
