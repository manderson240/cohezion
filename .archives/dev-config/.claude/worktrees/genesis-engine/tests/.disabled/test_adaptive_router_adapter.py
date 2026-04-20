"""Test AdaptiveRouterAdapter integration with TokenEfficientClient.

This test suite verifies that AdaptiveRouterAdapter is a drop-in replacement
for SmartRouterAdapter while maintaining the same interface contract.
"""

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


class TestModelSelection:
    """Verify ModelSelection dataclass works correctly."""

    def test_model_selection_with_defaults(self):
        """Verify ModelSelection has all expected attributes."""
        selection = ModelSelection(name="test-model")

        assert selection.name == "test-model"
        assert selection.confidence == 1.0
        assert selection.fallback_chain == []
        assert selection.reasoning == ""

    def test_model_selection_with_fallback_chain(self):
        """Verify fallback_chain is properly initialized."""
        fallbacks = ["model-b", "model-c"]
        selection = ModelSelection(
            name="model-a",
            confidence=0.8,
            fallback_chain=fallbacks,
            reasoning="because X",
        )

        assert selection.name == "model-a"
        assert selection.fallback_chain == fallbacks
        assert len(selection.fallback_chain) == 2


class TestOutcomeRecording:
    """Verify outcome recording for learning."""

    @pytest.mark.asyncio
    async def test_record_outcome_success(self, adapter: AdaptiveRouterAdapter):
        """Verify recording of successful execution."""
        adapter._selector.record_outcome = AsyncMock()

        await adapter.record_outcome(
            request_id="req-123",
            success=True,
            actual_latency_ms=450.5,
            actual_tps=25.3,
            failure_reason=None,
            model_used="qwen2.5-coder:14b",
        )

        adapter._selector.record_outcome.assert_called_once()
        call_args = adapter._selector.record_outcome.call_args
        assert call_args.kwargs["request_id"] == "req-123"
        assert call_args.kwargs["success"] is True

    @pytest.mark.asyncio
    async def test_record_outcome_failure(self, adapter: AdaptiveRouterAdapter):
        """Verify recording of failed execution."""
        adapter._selector.record_outcome = AsyncMock()

        await adapter.record_outcome(
            request_id="req-456",
            success=False,
            actual_latency_ms=5000.0,
            failure_reason="timeout",
            model_used="qwen3-coder:30b",
        )

        adapter._selector.record_outcome.assert_called_once()
        call_args = adapter._selector.record_outcome.call_args
        assert call_args.kwargs["success"] is False
        assert call_args.kwargs["failure_reason"] == "timeout"


class TestMetricsExport:
    """Verify metrics are properly exported."""

    @pytest.mark.asyncio
    async def test_get_metrics(self, adapter: AdaptiveRouterAdapter):
        """Verify metrics export."""
        metrics = await adapter.get_metrics()

        assert "adapter" in metrics
        assert metrics["adapter"] == "adaptive"
        assert "decisions_made" in metrics
        assert metrics["decisions_made"] >= 0


class TestFallback:
    """Verify fallback behavior when selector fails."""

    @pytest.mark.asyncio
    async def test_fallback_on_exception(self):
        """Verify adapter falls back to phi3:mini on exceptions."""
        selector = AsyncMock()
        selector.select_optimal_model.side_effect = Exception("Selector error")

        adapter = AdaptiveRouterAdapter(selector)

        result = await adapter.select_optimal_model({"task_type": "coding", "context_length": 100})

        assert result.name == "phi3:mini"
        assert result.confidence == 0.5
