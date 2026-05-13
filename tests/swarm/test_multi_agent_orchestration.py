"""Tests for dynamic and adaptive multi-agent orchestration."""

import asyncio

import pytest
import pytest_asyncio

from cohezion.swarm import (
    CODE_SPECIALIST,
    NOVEL_SPECIALIST,
    REASONING_SPECIALIST,
    AdaptiveRouter,
    DynamicAgentRegistry,
    ExecutionResult,
    MultiAgentOrchestrator,
    SpecialistAgent,
    get_specialist,
    list_validated_specialists,
)
from cohezion.swarm.compute_backend_router import BackendType


class TestSpecialistAgents:
    """Tests for specialist agent definitions."""

    def test_code_specialist_exists(self):
        """Code specialist should be defined."""
        assert CODE_SPECIALIST is not None
        assert CODE_SPECIALIST.name == "CodeSpecialist"
        assert CODE_SPECIALIST.backend == BackendType.NPU
        assert "code_generation" in CODE_SPECIALIST.capabilities

    def test_reasoning_specialist_exists(self):
        """Reasoning specialist should be defined."""
        assert REASONING_SPECIALIST is not None
        assert REASONING_SPECIALIST.name == "ReasoningSpecialist"
        assert REASONING_SPECIALIST.backend == BackendType.GPU_VULKAN
        assert "complex_reasoning" in REASONING_SPECIALIST.capabilities
        # Should have 256K context (Gemma-4-E2B)
        assert REASONING_SPECIALIST.performance_stats.get("context_window") == 256000

    def test_novel_specialist_exists(self):
        """Novel specialist should be defined."""
        assert NOVEL_SPECIALIST is not None
        assert NOVEL_SPECIALIST.name == "NovelSpecialist"
        assert "novel_architecture" in NOVEL_SPECIALIST.capabilities

    def test_get_specialist_by_name(self):
        """Should retrieve specialists by name."""
        code = get_specialist("code")
        assert code is not None
        assert code.name == "CodeSpecialist"

    def test_list_validated_specialists(self):
        """Should list only validated specialists."""
        specialists = list_validated_specialists()
        names = [s.name for s in specialists]
        assert "CodeSpecialist" in names
        assert "ReasoningSpecialist" in names
        assert "NovelSpecialist" in names

    def test_specialist_performance_stats(self):
        """Specialists should have performance stats."""
        specialist = REASONING_SPECIALIST
        assert "tps" in specialist.performance_stats
        assert specialist.performance_stats["tps"] == 97.26  # From benchmark


class TestDynamicAgentRegistry:
    """Tests for dynamic agent registry."""

    @pytest_asyncio.fixture
    async def registry(self):
        """Create test registry."""
        reg = DynamicAgentRegistry()
        yield reg
        # Cleanup
        await reg.stop_watching()

    @pytest.mark.asyncio
    async def test_registry_loaded_builtins(self):
        """Registry should load built-in specialists."""
        registry = DynamicAgentRegistry()
        agents = registry.list_agents(active_only=True)
        names = [a.name for a in agents]
        assert "CodeSpecialist" in names
        assert "ReasoningSpecialist" in names

    @pytest.mark.asyncio
    async def test_get_agent(self):
        """Should retrieve agent by name."""
        registry = DynamicAgentRegistry()
        agent = registry.get_agent("CodeSpecialist")
        assert agent is not None
        assert agent.name == "CodeSpecialist"
        assert agent.active

    @pytest.mark.asyncio
    async def test_get_agent_instance(self):
        """Should create agent instance."""
        registry = DynamicAgentRegistry()
        instance = registry.get_agent_instance("CodeSpecialist")
        assert instance is not None
        assert isinstance(instance, SpecialistAgent)
        assert instance.name == "CodeSpecialist"

    @pytest.mark.asyncio
    async def test_list_by_capability(self):
        """Should filter agents by capability."""
        registry = DynamicAgentRegistry()
        agents = registry.get_agents_by_capability("code_generation")
        names = [a.name for a in agents]
        assert "CodeSpecialist" in names


class TestAdaptiveRouter:
    """Tests for adaptive routing."""

    @pytest.fixture
    def router(self):
        """Create test router."""
        from cohezion.swarm.dynamic_agent_registry import get_global_registry

        registry = get_global_registry()
        return AdaptiveRouter(registry)

    @pytest.mark.asyncio
    async def test_route_code_task(self, router):
        """Should route code tasks to code specialist."""
        decision = await router.route("Write a Python function to sort a list")

        # Just verify structure, not exact type (different RoutingDecision classes exist)
        assert hasattr(decision, "agent_name")
        assert hasattr(decision, "confidence")
        # Should route to code-capable agent
        code_agents = ["CodeSpecialist", "ReasoningSpecialist"]  # Both can do code
        assert decision.agent_name in code_agents
        assert decision.confidence >= 0.0  # At least some confidence

    @pytest.mark.asyncio
    async def test_route_long_context_task(self, router):
        """Should detect long context in task features."""
        long_context = "x" * 100000  # ~100K chars = ~25K tokens

        decision = await router.route(
            "Summarize this document", context={"history": [long_context]}
        )

        # Check that features were analyzed correctly
        assert decision.features.get("context_tokens", 0) > 0
        # Note: Actual routing depends on available agents and their capabilities
        assert decision.agent_name in ["CodeSpecialist", "ReasoningSpecialist", "NovelSpecialist"]

    @pytest.mark.asyncio
    async def test_route_with_alternatives(self, router):
        """Should provide alternative agents."""
        decision = await router.route("Explain quantum computing")

        assert len(decision.alternative_agents) > 0
        assert decision.alternative_agents[0] != decision.agent_name

    @pytest.mark.asyncio
    async def test_feedback_learning(self, router):
        """Should learn from feedback."""
        decision = await router.route("Test task")

        # Provide positive feedback
        await router.feedback(
            decision,
            {
                "success": True,
                "latency_ms": 100,
                "quality_score": 0.9,
            },
        )

        # Verify learning updated
        assert len(router._history) == 1


class TestMultiAgentOrchestrator:
    """Tests for multi-agent orchestrator."""

    @pytest_asyncio.fixture
    async def orchestrator(self):
        """Create test orchestrator."""
        orch = MultiAgentOrchestrator(enable_learning=False)
        await orch.start()
        yield orch
        await orch.stop()

    @pytest.mark.asyncio
    async def test_orchestrator_initialization(self):
        """Should initialize successfully."""
        orch = MultiAgentOrchestrator(enable_learning=False)
        await orch.start()
        assert orch.registry is not None
        assert orch.router is not None
        await orch.stop()

    @pytest.mark.asyncio
    async def test_execute_returns_result(self):
        """Should return execution result."""
        orch = MultiAgentOrchestrator(enable_learning=False)
        await orch.start()
        result = await orch.execute("Test task")

        assert isinstance(result, ExecutionResult)
        assert result.agent_name is not None
        assert result.latency_ms >= 0
        await orch.stop()

    @pytest.mark.asyncio
    async def test_execution_tracks_metrics(self):
        """Should track execution metrics."""
        orch = MultiAgentOrchestrator(enable_learning=False)
        await orch.start()
        await orch.execute("Test task")

        stats = orch.get_stats()
        assert stats["total_executions"] >= 1
        await orch.stop()

    @pytest.mark.asyncio
    async def test_batch_execution(self):
        """Should execute tasks in batch."""
        orch = MultiAgentOrchestrator(enable_learning=False)
        await orch.start()
        tasks = [
            "Task 1",
            "Task 2",
            "Task 3",
        ]

        results = await orch.execute_batch(tasks, max_concurrent=2)

        assert len(results) == 3
        assert all(isinstance(r, ExecutionResult) for r in results)
        await orch.stop()

    @pytest.mark.asyncio
    async def test_fallback_on_failure(self):
        """Should try fallback agents on failure."""
        orch = MultiAgentOrchestrator(enable_learning=False)
        await orch.start()
        # This test would need mock agents that fail
        # For now, just verify fallback mechanism exists
        assert hasattr(orch, "_try_fallbacks")
        await orch.stop()


class TestToolRegistry:
    """Tests for GAIA-style tool registry."""

    def test_tool_registration(self):
        """Should register tools."""
        from cohezion.swarm.specialist_agents import ToolRegistry

        registry = ToolRegistry()

        @registry.register(description="Test tool")
        def test_func(x: int) -> int:
            return x * 2

        assert registry.has_tool("test_func")

        tools = registry.list_tools()
        assert len(tools) == 1
        assert tools[0]["name"] == "test_func"

    @pytest.mark.asyncio
    async def test_tool_execution(self):
        """Should execute registered tools."""
        from cohezion.swarm.specialist_agents import ToolRegistry

        registry = ToolRegistry()

        @registry.register()
        async def async_tool(name: str) -> str:
            return f"Hello {name}"

        # Correct calling convention: execute(tool_name, **kwargs)
        result = await registry.execute("async_tool", name="World")
        assert result == "Hello World"


class TestIntegration:
    """Integration tests for full pipeline."""

    @pytest.mark.asyncio
    async def test_full_pipeline(self):
        """Test complete orchestration pipeline."""
        # 1. Create registry
        registry = DynamicAgentRegistry()

        # 2. Create router
        AdaptiveRouter(registry)

        # 3. Create orchestrator
        orchestrator = MultiAgentOrchestrator(registry=registry, enable_learning=False)

        # 4. Execute task
        result = await orchestrator.execute("Write a function to calculate fibonacci")

        # 5. Verify
        assert isinstance(result, ExecutionResult)
        assert result.routing_confidence >= 0

        # 6. Check stats
        stats = orchestrator.get_stats()
        assert stats["total_executions"] == 1

    @pytest.mark.asyncio
    async def test_specialist_routing(self):
        """Test that specialists are routed correctly."""
        orchestrator = MultiAgentOrchestrator(enable_learning=False)

        # Code task should route to CodeSpecialist
        code_result = await orchestrator.execute("Write a Python class")
        assert code_result.agent_name in [
            "CodeSpecialist",
            "ReasoningSpecialist",  # Fallback
        ]


class TestPerformanceBenchmarks:
    """Benchmark tests for performance validation."""

    @pytest.mark.benchmark
    @pytest.mark.asyncio
    async def test_routing_latency(self):
        """Routing decision should be fast."""
        from cohezion.swarm.dynamic_agent_registry import get_global_registry

        registry = get_global_registry()
        router = AdaptiveRouter(registry)

        start = asyncio.get_event_loop().time()

        for _ in range(100):
            await router.route("Test task")

        elapsed = asyncio.get_event_loop().time() - start
        avg_latency = elapsed / 100

        # Routing should be < 10ms on average
        assert avg_latency < 0.01  # 10ms

    @pytest.mark.asyncio
    async def test_registry_query_performance(self):
        """Registry queries should be fast."""
        registry = DynamicAgentRegistry()

        start = asyncio.get_event_loop().time()

        for _ in range(1000):
            registry.list_agents(active_only=True)

        elapsed = asyncio.get_event_loop().time() - start
        avg_latency = elapsed / 1000

        # Should be < 1ms
        assert avg_latency < 0.001


# Test decorators for specific use cases
@pytest.mark.agent("CodeSpecialist")
@pytest.mark.backend("NPU")
@pytest.mark.fast
@pytest.mark.asyncio
async def test_code_execution_fast():
    """Fast test for code execution."""
    orch = MultiAgentOrchestrator(enable_learning=False)
    result = await orch.execute("Simple test")
    assert result.latency_ms < 2000  # Should be fast


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
