"""Test AdaptiveRouterAdapter integration with TokenEfficientClient."""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock

import pytest

from cohezion.swarm.adaptive_router_adapter import (
    AdaptiveRouterAdapter,
    ModelSelection,
)


@pytest.fixture
def mock_selector() -> Mock:
    """Create a mock AdaptiveModelSelector."""
    selector = AsyncMock()
    selector.select_optimal_model = AsyncMock()
    selector.record_outcome = AsyncMock()
    selector.profile_manager = Mock()
    selector.profile_manager.profiles = {}
    return selector


@pytest.fixture
def adapter(mock_selector: Mock) -> AdaptiveRouterAdapter:
    """Create an adapter with mock selector."""
    return AdaptiveRouterAdapter(mock_selector)


class TestInterfaceContract:
    """Verify AdaptiveRouterAdapter has same interface as SmartRouterAdapter."""

    @pytest.mark.asyncio
    async def test_select_optimal_model_signature(self, adapter: AdaptiveRouterAdapter):
        """Verify select_optimal_model has expected signature."""
        from cohezion.swarm.hardware_aware_router import RoutingDecision

        adapter._selector.select_optimal_model.return_value = RoutingDecision(
            request_id="test-1",
            primary_model="qwen3-coder:30b",
            fallback_chain=["qwen2.5-coder:14b", "phi4:latest"],
            confidence=0.85,
            predicted_tps=8.0,
            predicted_latency_ms=1000,
            reasoning="Selected for coding task",
        )

        result = await adapter.select_optimal_model({
            "task_type": "coding",
            "context_length": 1024,
        })

        assert hasattr(result, "name")
        assert result.name == "qwen3-coder:30b"


class TestFallback:
    """Verify fallback behavior when selector fails."""

    @pytest.mark.asyncio
    async def test_fallback_on_exception(self):
        """Verify adapter falls back to phi3:mini on exceptions."""
        selector = AsyncMock()
        selector.select_optimal_model.side_effect = Exception("Selector error")

        adapter = AdaptiveRouterAdapter(selector)

        result = await adapter.select_optimal_model({
            "task_type": "coding",
            "context_length": 100,
        })

        assert result.name == "phi3:mini"
        assert result.confidence == 0.5
