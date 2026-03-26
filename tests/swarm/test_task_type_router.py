"""Tests for TaskTypeRouter."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from cohezion.swarm.providers.model_provider import GenerationResult
from cohezion.swarm.task_type_router import (
    ProviderTier,
    RouteEntry,
    TaskTypeRouter,
)


def _make_result(provider: str = "ollama", model: str = "test") -> GenerationResult:
    return GenerationResult(
        response="test response",
        model=model,
        provider=provider,
        confidence=0.9,
        tokens_used=100,
        latency_ms=50.0,
        metadata={},
    )


def _mock_provider(provider_name: str = "ollama") -> AsyncMock:
    mock = AsyncMock()
    mock.generate = AsyncMock(return_value=_make_result(provider_name))
    return mock


class TestTaskTypeRouter:
    def test_route_coding_to_local(self):
        """Coding tasks should route to local Ollama first."""
        router = TaskTypeRouter()
        local = _mock_provider("ollama")
        router.register_provider(ProviderTier.LOCAL, local)

        import asyncio

        result = asyncio.get_event_loop().run_until_complete(
            router.route_and_execute("Write hello world", "coding")
        )
        assert result.provider == "ollama"
        local.generate.assert_called_once()

    def test_route_complex_reasoning_to_anthropic(self):
        """Complex reasoning should route to Anthropic first."""
        router = TaskTypeRouter()
        anthropic = _mock_provider("anthropic")
        local = _mock_provider("ollama")
        router.register_provider(ProviderTier.ANTHROPIC, anthropic)
        router.register_provider(ProviderTier.LOCAL, local)

        import asyncio

        result = asyncio.get_event_loop().run_until_complete(
            router.route_and_execute("Explain quantum mechanics", "complex_reasoning")
        )
        assert result.provider == "anthropic"
        anthropic.generate.assert_called_once()
        local.generate.assert_not_called()

    def test_fallback_when_primary_fails(self):
        """When primary provider fails, should cascade to fallback."""
        router = TaskTypeRouter()
        local = AsyncMock()
        local.generate = AsyncMock(side_effect=RuntimeError("Ollama down"))
        cloud = _mock_provider("ollama-cloud")
        router.register_provider(ProviderTier.LOCAL, local)
        router.register_provider(ProviderTier.OLLAMA_CLOUD, cloud)

        import asyncio

        result = asyncio.get_event_loop().run_until_complete(
            router.route_and_execute("Write code", "coding")
        )
        assert result.provider == "ollama-cloud"

    def test_budget_gate_blocks_expensive(self):
        """Budget gate should block expensive providers and cascade."""
        mock_enforcer = MagicMock()
        mock_enforcer.check_budget = MagicMock(return_value=(False, "over budget"))

        router = TaskTypeRouter(budget_enforcer=mock_enforcer)
        anthropic = _mock_provider("anthropic")
        local = _mock_provider("ollama")
        router.register_provider(ProviderTier.ANTHROPIC, anthropic)
        router.register_provider(ProviderTier.LOCAL, local)

        import asyncio

        result = asyncio.get_event_loop().run_until_complete(
            router.route_and_execute("Analyze data", "analysis")
        )
        # Anthropic blocked by budget, should fall back to local
        assert result.provider == "ollama"
        anthropic.generate.assert_not_called()

    def test_all_providers_fail_raises(self):
        """When all providers fail, should raise RuntimeError."""
        router = TaskTypeRouter()
        local = AsyncMock()
        local.generate = AsyncMock(side_effect=RuntimeError("down"))
        router.register_provider(ProviderTier.LOCAL, local)

        # Use summary task type which only has local providers
        import asyncio

        with pytest.raises(RuntimeError, match="All providers exhausted"):
            asyncio.get_event_loop().run_until_complete(
                router.route_and_execute("Summarize text", "summary")
            )

    def test_local_bypass_budget_check(self):
        """Local ($0) models should bypass budget check entirely."""
        mock_enforcer = MagicMock()
        mock_enforcer.check_budget = MagicMock(return_value=(False, "over budget"))

        router = TaskTypeRouter(budget_enforcer=mock_enforcer)
        local = _mock_provider("ollama")
        router.register_provider(ProviderTier.LOCAL, local)

        import asyncio

        # Summary only has local entries, budget gate shouldn't block
        result = asyncio.get_event_loop().run_until_complete(
            router.route_and_execute("Summarize", "summary")
        )
        assert result.provider == "ollama"

    def test_routing_log_captures_decisions(self):
        """Routing decisions should be logged for observability."""
        router = TaskTypeRouter()
        local = _mock_provider("ollama")
        router.register_provider(ProviderTier.LOCAL, local)

        import asyncio

        asyncio.get_event_loop().run_until_complete(router.route_and_execute("Test", "coding"))

        assert len(router.routing_log) == 1
        decision = router.routing_log[0]
        assert decision.task_type == "coding"
        assert decision.success is True
        assert decision.provider == "ollama"

    def test_unknown_task_type_defaults(self):
        """Unknown task types should fall back to simple_qa routing."""
        router = TaskTypeRouter()
        local = _mock_provider("ollama")
        router.register_provider(ProviderTier.LOCAL, local)

        import asyncio

        result = asyncio.get_event_loop().run_until_complete(
            router.route_and_execute("Something unknown", "nonexistent_type")
        )
        assert result.provider == "ollama"

    def test_unregistered_provider_skipped(self):
        """Entries for unregistered providers should be silently skipped."""
        router = TaskTypeRouter()
        # Don't register Anthropic — analysis task should skip to local fallback
        local = _mock_provider("ollama")
        router.register_provider(ProviderTier.LOCAL, local)

        import asyncio

        result = asyncio.get_event_loop().run_until_complete(
            router.route_and_execute("Analyze this", "analysis")
        )
        assert result.provider == "ollama"

    def test_get_routing_stats(self):
        """Stats should summarize routing decisions."""
        router = TaskTypeRouter()
        local = _mock_provider("ollama")
        router.register_provider(ProviderTier.LOCAL, local)

        import asyncio

        asyncio.get_event_loop().run_until_complete(router.route_and_execute("Test 1", "coding"))
        asyncio.get_event_loop().run_until_complete(router.route_and_execute("Test 2", "summary"))

        stats = router.get_routing_stats()
        assert stats["total"] == 2
        assert stats["successes"] == 2
        assert stats["by_provider"]["ollama"] == 2
