"""Multi-agent orchestration with dynamic and adaptive capabilities.

Integrates:
- Dynamic agent registry (hot-reload, runtime registration)
- Adaptive routing (self-learning, performance-based)
- Hardware-aware execution (NPU/GPU/Cloud)
- Vault MCP integration (knowledge access)
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from cohezion.swarm.adaptive_router import (
    AdaptiveRouter,
    RoutingDecision,
)
from cohezion.swarm.dynamic_agent_registry import (
    DynamicAgentRegistry,
    get_global_registry,
)
from cohezion.swarm.specialist_agents import (
    SpecialistAgent,
)


logger = logging.getLogger(__name__)


@dataclass
class ExecutionResult:
    """Result of multi-agent task execution."""

    success: bool
    output: str | dict[str, Any]
    agent_name: str
    backend: str
    latency_ms: float
    tokens_used: int
    tools_invoked: list[str]
    quality_score: float
    routing_confidence: float
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "output": self.output if isinstance(self.output, str) else str(self.output)[:500],
            "agent": self.agent_name,
            "backend": self.backend,
            "latency_ms": round(self.latency_ms, 2),
            "tokens": self.tokens_used,
            "tools": self.tools_invoked,
            "quality": round(self.quality_score, 2),
            "routing_confidence": round(self.routing_confidence, 2),
            "time": self.timestamp.isoformat(),
        }


@dataclass
class TaskContext:
    """Context for task execution."""

    task_id: str
    prompt: str
    history: list[dict[str, Any]] = field(default_factory=list)
    tools_allowed: list[str] = field(default_factory=list)
    quality_requirement: float = 0.7
    timeout_seconds: float = 60.0
    use_tools: bool = True


class MultiAgentOrchestrator:
    """Production multi-agent orchestration system.

    Key capabilities:
    - Dynamic agent loading (hot-reload)
    - Adaptive routing (learns optimal agent)
    - Automatic fallback chains
    - Tool integration (external system access)
    - Performance tracking
    """

    def __init__(
        self,
        registry: DynamicAgentRegistry | None = None,
        enable_learning: bool = True,
        default_timeout: float = 60.0,
    ):
        self.registry = registry or get_global_registry()
        self.router = AdaptiveRouter(self.registry)
        self.enable_learning = enable_learning
        self.default_timeout = default_timeout

        # Execution cache
        self._execution_cache: dict[str, ExecutionResult] = {}
        self._learning_task: asyncio.Task | None = None

        # Metrics
        self._total_executions = 0
        self._successful_executions = 0

    async def start(self):
        """Start orchestration services."""
        # Start file watcher
        await self.registry.start_watching()
        logger.info("MultiAgentOrchestrator started")

    async def stop(self):
        """Stop orchestration services."""
        await self.registry.stop_watching()
        logger.info("MultiAgentOrchestrator stopped")

    async def execute(
        self,
        task: str,
        context: dict[str, Any] | None = None,
        timeout: float | None = None,
        fallback_on_error: bool = True,
    ) -> ExecutionResult:
        """Execute task with full orchestration.

        Args:
            task: Task description/prompt
            context: Optional execution context
            timeout: Maximum execution time
            fallback_on_error: Whether to try alternatives on failure

        Returns:
            ExecutionResult with full details
        """
        self._total_executions += 1
        timeout = timeout or self.default_timeout
        context = context or {}

        start_time = time.time()

        try:
            # 1. Get routing decision
            decision = await self.router.route(task, context)

            if not decision.agent_name:
                return self._error_result("No suitable agent found", start_time)

            # 2. Execute with primary agent
            result = await self._execute_with_agent(
                decision.agent_name,
                task,
                context,
                decision,
            )

            # 3. Handle failure with fallback
            if not result.success and fallback_on_error:
                result = await self._try_fallbacks(
                    decision,
                    task,
                    context,
                )

            # 4. Provide feedback for learning
            if self.enable_learning:
                await self._provide_feedback(decision, result)

            if result.success:
                self._successful_executions += 1

            return result

        except TimeoutError:
            return self._error_result(
                f"Execution timeout ({timeout}s)",
                start_time,
            )
        except Exception as e:
            logger.exception("Execution failed")
            return self._error_result(str(e), start_time)

    async def _execute_with_agent(
        self,
        agent_name: str,
        task: str,
        context: dict[str, Any],
        decision: RoutingDecision,
    ) -> ExecutionResult:
        """Execute task with specific agent."""
        start_time = time.time()

        # Get agent
        agent_module = self.registry.get_agent(agent_name)
        if not agent_module:
            return self._error_result(f"Agent {agent_name} not found", start_time)

        agent = agent_module.create_instance()

        # Prepare execution
        tool_names = self._select_tools(task, agent)

        try:
            # Execute
            agent_result = await asyncio.wait_for(
                agent.execute(task, context, use_tools=tool_names),
                timeout=self.default_timeout,
            )

            latency_ms = (time.time() - start_time) * 1000

            # Assess quality
            quality = self._assess_quality(agent_result)

            # Build result
            return ExecutionResult(
                success=agent_result.get("success", False),
                output=agent_result.get("result", {}).get("text", ""),
                agent_name=agent_name,
                backend=agent_result.get("backend", "unknown"),
                latency_ms=latency_ms,
                tokens_used=agent_result.get("result", {}).get("tokens", 0),
                tools_invoked=tool_names,
                quality_score=quality,
                routing_confidence=decision.confidence,
            )

        except TimeoutError:
            raise
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            return ExecutionResult(
                success=False,
                output=str(e),
                agent_name=agent_name,
                backend="unknown",
                latency_ms=latency_ms,
                tokens_used=0,
                tools_invoked=tool_names,
                quality_score=0.0,
                routing_confidence=decision.confidence,
            )

    async def _try_fallbacks(
        self,
        primary_decision: RoutingDecision,
        task: str,
        context: dict[str, Any],
    ) -> ExecutionResult:
        """Try alternative agents on failure."""

        for alt_name in primary_decision.alternative_agents:
            logger.info(f"Trying fallback: {alt_name}")

            try:
                # Create fallback decision
                fallback_decision = RoutingDecision(
                    agent_name=alt_name,
                    confidence=0.5,
                    reasoning="fallback",
                    alternative_agents=[],
                    expected_latency_ms=primary_decision.expected_latency_ms * 1.5,
                    expected_quality=primary_decision.expected_quality * 0.9,
                )

                result = await self._execute_with_agent(
                    alt_name,
                    task,
                    context,
                    fallback_decision,
                )

                if result.success:
                    return result

            except Exception as e:
                logger.warning(f"Fallback {alt_name} failed: {e}")
                continue

        # All fallbacks exhausted
        return self._error_result("All agent options exhausted", time.time())

    def _select_tools(self, task: str, agent: SpecialistAgent) -> list[str]:
        """Select appropriate tools for task."""
        selected = []

        # Check vault query for complex tasks
        if len(task) > 200 or "complex" in task.lower():
            if agent.tool_registry.has_tool("query_vault"):
                selected.append("query_vault")

        # Check model routing for large tasks
        if len(task) > 1000:
            if agent.tool_registry.has_tool("route_to_backend"):
                selected.append("route_to_backend")

        return selected

    def _assess_quality(self, result: dict[str, Any]) -> float:
        """Heuristic quality assessment."""
        text = str(result.get("result", {}).get("text", ""))

        score = 0.5

        # Length check
        if 50 < len(text) < 5000:
            score += 0.1

        # Structure check
        if "\n" in text and not text.endswith("..."):
            score += 0.1

        # Error check
        if "error" not in text.lower() and "failed" not in text.lower():
            score += 0.1

        # Success boost
        if result.get("success", False):
            score += 0.2

        return min(score, 1.0)

    async def _provide_feedback(
        self,
        decision: RoutingDecision,
        result: ExecutionResult,
    ):
        """Provide feedback to router for learning."""
        try:
            await self.router.feedback(
                decision,
                {
                    "success": result.success,
                    "latency_ms": result.latency_ms,
                    "quality_score": result.quality_score,
                    "features": decision.features,
                },
            )
        except Exception as e:
            logger.warning(f"Feedback failed: {e}")

    def _error_result(self, message: str, start_time: float) -> ExecutionResult:
        """Create error result."""
        return ExecutionResult(
            success=False,
            output=message,
            agent_name="none",
            backend="none",
            latency_ms=(time.time() - start_time) * 1000,
            tokens_used=0,
            tools_invoked=[],
            quality_score=0.0,
            routing_confidence=0.0,
        )

    # ═══════════════════════════════════════════════════════════════════
    # Batch Execution
    # ═══════════════════════════════════════════════════════════════════

    async def execute_batch(
        self,
        tasks: list[str],
        context: dict | None = None,
        max_concurrent: int = 5,
    ) -> list[ExecutionResult]:
        """Execute multiple tasks concurrently.

        Args:
            tasks: List of task descriptions
            context: Shared context for all tasks
            max_concurrent: Maximum concurrent executions

        Returns:
            List of ExecutionResults
        """
        semaphore = asyncio.Semaphore(max_concurrent)

        async def execute_with_limit(task: str) -> ExecutionResult:
            async with semaphore:
                return await self.execute(task, context)

        results = await asyncio.gather(*[execute_with_limit(t) for t in tasks])

        return results

    # ═══════════════════════════════════════════════════════════════════
    # Analytics
    # ═══════════════════════════════════════════════════════════════════

    def get_stats(self) -> dict[str, Any]:
        """Get orchestration statistics."""
        success_rate = self._successful_executions / max(self._total_executions, 1)

        return {
            "total_executions": self._total_executions,
            "successful_executions": self._successful_executions,
            "success_rate": success_rate,
            "registry_status": self._get_registry_summary(),
            "router_stats": self.router.get_routing_stats(),
        }

    def _get_registry_summary(self) -> dict[str, Any]:
        """Get summary of registered agents."""
        agents = self.registry.list_agents(active_only=True)

        return {
            "active_agents": len(agents),
            "agents": [
                {
                    "name": a.name,
                    "capabilities": a.capabilities,
                    "performance": a.performance_stats,
                }
                for a in agents
            ],
        }

    def print_report(self):
        """Print comprehensive report."""
        stats = self.get_stats()

        print("\n" + "=" * 70)
        print("MULTI-AGENT ORCHESTRATION REPORT")
        print("=" * 70)

        print("\n📊 Execution Statistics:")
        print(f"  Total executions: {stats['total_executions']}")
        print(f"  Success rate: {stats['success_rate']:.1%}")

        print(f"\n🤖 Active Agents: {stats['registry_status']['active_agents']}")
        for agent in stats["registry_status"]["agents"]:
            print(f"  - {agent['name']}: {', '.join(agent['capabilities'][:3])}")

        if stats.get("router_stats"):
            rs = stats["router_stats"]
            print("\n🧠 Routing Intelligence:")
            print(f"  Total routings: {rs.get('total_routings', 0)}")
            print(f"  Average confidence: {rs.get('avg_confidence', 0):.2f}")
            print(f"  Learning progress: {rs.get('learning_progress', 0)} task types")

        print("\n" + "=" * 70)


# ═══════════════════════════════════════════════════════════════════════════
# Convenience Functions
# ═══════════════════════════════════════════════════════════════════════════

_orchestrator: MultiAgentOrchestrator | None = None


async def get_orchestrator() -> MultiAgentOrchestrator:
    """Get or create global orchestrator."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = MultiAgentOrchestrator()
        await _orchestrator.start()
    return _orchestrator


async def execute_task(task: str, context: dict | None = None, **kwargs) -> ExecutionResult:
    """Quick execution function."""
    orch = await get_orchestrator()
    return await orch.execute(task, context, **kwargs)


async def quick_orchestrate(task: str) -> str:
    """Simplified interface returning just the output."""
    result = await execute_task(task)
    return str(result.output) if result.success else f"Error: {result.output}"


# Example usage
if __name__ == "__main__":

    async def demo():
        """Demonstrate multi-agent orchestration."""
        print("🚀 Multi-Agent Orchestration Demo")
        print("=" * 50)

        # Initialize
        orch = MultiAgentOrchestrator()
        await orch.start()

        # Demo tasks
        tasks = [
            "Write a Python function to calculate fibonacci",
            "Explain quantum computing to a 10-year-old",
            "Summarize the benefits of microservices architecture",
        ]

        for task in tasks:
            print(f"\n📝 Task: {task[:50]}...")
            result = await orch.execute(task)
            print(f"   Agent: {result.agent_name}")
            print(f"   Backend: {result.backend}")
            print(f"   Confidence: {result.routing_confidence:.2f}")
            print(f"   Latency: {result.latency_ms:.1f}ms")
            print(f"   Success: {'✅' if result.success else '❌'}")

        # Print report
        orch.print_report()

        # Shutdown
        await orch.stop()

    # Run demo
    asyncio.run(demo())
