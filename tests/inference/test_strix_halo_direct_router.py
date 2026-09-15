"""Unit tests for StrixHaloDirectRouter."""

from unittest.mock import MagicMock

import httpx
import pytest

from cohezion.inference.strix_halo_direct_router import (
    DirectInferenceResponse,
    DirectTaskTier,
    StrixHaloDirectRouter,
)
from cohezion.inference.strix_halo_optimizer import StrixHaloSiliconOptimizer


@pytest.fixture
def mock_optimizer():
    opt = MagicMock(spec=StrixHaloSiliconOptimizer)
    from cohezion.inference.strix_halo_optimizer import StrixHaloTopology

    opt.get_strix_halo_topology.return_value = StrixHaloTopology()
    opt.enforce_wave32_environment.return_value = {"ROCM_WAVEFRONT_SIZE": "32"}
    return opt


def test_select_optimal_tier(mock_optimizer):
    router = StrixHaloDirectRouter(optimizer=mock_optimizer)

    # NPU low-power drafting & fast classification
    assert router.select_optimal_tier("short_categorical") == DirectTaskTier.TIER0_NPU
    assert router.select_optimal_tier("draft") == DirectTaskTier.TIER0_NPU
    assert router.select_optimal_tier("fast_qa") == DirectTaskTier.TIER0_NPU

    # Vulkan small for tools and structured generation
    assert router.select_optimal_tier("tools") == DirectTaskTier.TIER1_VULKAN_SMALL
    assert router.select_optimal_tier("structured") == DirectTaskTier.TIER1_VULKAN_SMALL

    # Embeddings
    assert router.select_optimal_tier("embeddings") == DirectTaskTier.TIER1_VULKAN_EMBED

    # ROCm heavy for reasoning and coding
    assert (
        router.select_optimal_tier("reasoning", requires_reasoning=True)
        == DirectTaskTier.TIER1_ROCM_HEAVY
    )
    assert (
        router.select_optimal_tier("coding", requires_coding=True)
        == DirectTaskTier.TIER1_ROCM_HEAVY
    )


def test_port_and_model_mapping(mock_optimizer):
    router = StrixHaloDirectRouter(optimizer=mock_optimizer)

    assert router._tier_to_port(DirectTaskTier.TIER0_NPU) == 8002
    assert router._tier_to_port(DirectTaskTier.TIER1_VULKAN_SMALL) == 8003
    assert router._tier_to_port(DirectTaskTier.TIER1_VULKAN_EMBED) == 8005
    assert router._tier_to_port(DirectTaskTier.TIER1_ROCM_HEAVY) == 8006
    assert router._tier_to_port(DirectTaskTier.LEMONADE_OMNI) == 13305
    assert router._tier_to_port(DirectTaskTier.TIER2_OLLAMA_CLOUD) == 11434

    assert router._tier_to_default_model(DirectTaskTier.TIER0_NPU) == "llama3.2:1b"
    assert "Bonsai" in router._tier_to_default_model(DirectTaskTier.TIER1_VULKAN_SMALL)
    assert "nomic" in router._tier_to_default_model(DirectTaskTier.TIER1_VULKAN_EMBED)
    assert "gemma" in router._tier_to_default_model(DirectTaskTier.TIER1_ROCM_HEAVY)


@pytest.mark.asyncio
async def test_execute_direct_success(mock_optimizer):
    router = StrixHaloDirectRouter(optimizer=mock_optimizer)

    mock_response = {
        "choices": [{"message": {"content": "42"}}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 2},
    }

    mock_client = MagicMock(spec=httpx.AsyncClient)
    mock_http_resp = MagicMock(spec=httpx.Response)
    mock_http_resp.status_code = 200
    mock_http_resp.json.return_value = mock_response
    mock_http_resp.raise_for_status = MagicMock()

    async def mock_post(*args, **kwargs):
        return mock_http_resp

    mock_client.post = mock_post

    resp = await router.execute_direct(
        prompt="What is the answer?",
        tier=DirectTaskTier.TIER0_NPU,
        client=mock_client,
    )

    assert isinstance(resp, DirectInferenceResponse)
    assert resp.content == "42"
    assert resp.tier == DirectTaskTier.TIER0_NPU
    assert resp.port == 8002
    assert resp.tokens_evaluated == 10
    assert resp.tokens_generated == 2
    assert resp.verified is True


@pytest.mark.asyncio
async def test_execute_direct_resilient_cascade(mock_optimizer):
    router = StrixHaloDirectRouter(optimizer=mock_optimizer)

    # Setup client that fails on tier0 (port 8002) but succeeds on fallback tier1 (port 8003)
    mock_client = MagicMock(spec=httpx.AsyncClient)

    call_count = 0

    async def mock_post(url, *args, **kwargs):
        nonlocal call_count
        call_count += 1
        if "8002" in url:
            raise httpx.ConnectError("NPU socket busy")

        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "Cascade response from Vulkan"}}],
            "usage": {"prompt_tokens": 8, "completion_tokens": 4},
        }
        mock_resp.raise_for_status = MagicMock()
        return mock_resp

    mock_client.post = mock_post

    resp = await router.execute_direct(
        prompt="Test cascading",
        tier=DirectTaskTier.TIER0_NPU,
        client=mock_client,
    )

    assert resp.verified is True
    assert resp.content == "Cascade response from Vulkan"
    assert resp.port == 8003
    assert resp.tier == DirectTaskTier.TIER1_VULKAN_SMALL
    assert call_count >= 2


@pytest.mark.asyncio
async def test_execute_direct_safety_fallback(mock_optimizer):
    router = StrixHaloDirectRouter(optimizer=mock_optimizer)

    mock_client = MagicMock(spec=httpx.AsyncClient)

    async def mock_post(*args, **kwargs):
        raise httpx.ConnectError("All ports down")

    mock_client.post = mock_post

    resp = await router.execute_direct(
        prompt="Test total outage",
        tier=DirectTaskTier.TIER0_NPU,
        client=mock_client,
    )

    assert resp.verified is False
    assert "STRIX HALO SENTINEL" in resp.content
    assert resp.details.get("status") == "safety_fallback"
