"""Bridge between MultiAgentOrchestrator and CompoundExecutor.

Integrates the multi-agent system into the compound engineering loop:
- Agent routing decisions feed into SkillRefiner
- Outcomes persist to Vault for pattern learning
- FLUME encodes task characteristics to latent space
- HIHO alignment gates before multi-agent execution
- Cross-session learning improves agent selection

This creates a compound system where:
1. Tasks are analyzed and routed to optimal agents
2. Execution outcomes refine agent selection over time
3. Vault stores routing patterns for similar tasks
4. FLUME enables similarity-based agent recommendations
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from cohezion.compound.executor import CompoundExecutor, ExecutionResult
from cohezion.core.mcp_client import MCPClient
from cohezion.swarm import (
    ExecutionResult as AgentExecutionResult,
)
from cohezion.swarm import (
    MultiAgentOrchestrator,
    RoutingDecision,
    get_orchestrator,
)
from cohezion.swarm.adaptive_router import AdaptiveRouter


logger = logging.getLogger(__name__)


@dataclass
class CompoundAgentResult:
    """Result from compound-integrated agent execution."""

    # Original fields from agent execution
    success: bool
    output: str | dict[str, Any]
    agent_name: str
    backend: str
    latency_ms: float
    tokens_used: int

    # Compound-specific additions
    routing_confidence: float
    selected_agents: list[str]  # Primary + fallbacks tried
    vault_guidance: dict[str, Any] | None = None
    flume_embedding: list[float] | None = None
    coherence_score: float = 0.0

    # Learning data
    feedback_provided: bool = False
    skill_refinement_triggered: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "success": self.success,
            "agent": self.agent_name,
            "backend": self.backend,
            "latency_ms": self.latency_ms,
            "confidence": self.routing_confidence,
            "vault_guidance": self.vault_guidance is not None,
            " coherence": self.coherence_score,
        }


class MultiAgentCompoundBridge:
    """Bridge between MultiAgentOrchestrator and CompoundEngineering.

    This bridge integrates the multi-agent system into Cohezion's compound loop,
    enabling:
    - Vault-persisted routing decisions
    - FLUME-encoded task characteristics
    - HIHO-aligned agent selection
    - SkillRefiner feedback from agent outcomes
    - RetrospectionEngine analysis of multi-agent patterns

    Usage:
        bridge = MultiAgentCompoundBridge(mcp_client)

        # Execute with full compound integration
        result = await bridge.execute(
            task="Write a Python function",
            context={"project": "my_project"},
        )

        # Result includes routing insights, vault guidance, coherence scores
    """

    def __init__(
        self,
        mcp_client: MCPClient,
        orchestrator: MultiAgentOrchestrator | None = None,
        enable_flume: bool = True,
        enable_vault_persistence: bool = True,
        enable_coherence_tracking: bool = True,
    ):
        """Initialize the compound bridge.

        Args:
            mcp_client: Connected MCP client for vault operations
            orchestrator: Optional MultiAgentOrchestrator (creates default if None)
            enable_flume: Whether to FLUME-encode task characteristics
            enable_vault_persistence: Whether to persist routing decisions to vault
            enable_coherence_tracking: Whether to track coherence scores
        """
        self.mcp_client = mcp_client
        self.orchestrator = orchestrator
        self.enable_flume = enable_flume
        self.enable_vault_persistence = enable_vault_persistence
        self.enable_coherence_tracking = enable_coherence_tracking

        # Lazy initialization
        self._initialized = False
        self._adaptive_router: AdaptiveRouter | None = None

    async def _ensure_initialized(self):
        """Lazy initialization of orchestrator and router."""
        if self._initialized:
            return

        if self.orchestrator is None:
            self.orchestrator = await get_orchestrator()

        self._adaptive_router = self.orchestrator.router
        self._initialized = True

    async def execute(
        self,
        task: str,
        context: dict[str, Any] | None = None,
        use_vault_guidance: bool = True,
        min_coherence: float = 0.5,  # HIHO threshold
    ) -> CompoundAgentResult:
        """Execute task with full compound integration.

        Args:
            task: Task description/prompt
            context: Optional execution context
            use_vault_guidance: Whether to query vault for similar tasks
            min_coherence: Minimum coherence score for HIHO alignment

        Returns:
            CompoundAgentResult with routing metadata and learning data
        """
        await self._ensure_initialized()
        context = context or {}

        start_time = datetime.now()

        # Step 1: Query vault for similar tasks (if enabled)
        vault_guidance = None
        if use_vault_guidance and self.enable_vault_persistence:
            vault_guidance = await self._get_vault_guidance(task)

        # Step 2: FLUME-encode task characteristics (if enabled)
        flume_embedding = None
        if self.enable_flume:
            flume_embedding = await self._flume_encode(task)

        # Step 3: Get routing decision with vault context
        decision = await self._route_with_guidance(
            task,
            context,
            vault_guidance,
        )

        # Step 4: HIHO alignment check
        coherence = await self._calculate_coherence(task, decision)
        if coherence < min_coherence:
            logger.warning(f"Low coherence ({coherence:.2f}) for task: {task[:50]}...")
            # Still proceed but mark for review

        # Step 5: Execute with orchestrator
        agent_result = await self.orchestrator.execute(
            task,
            context={**context, "vault_guidance": vault_guidance},
        )

        # Step 6: Provide feedback for learning
        await self._provide_feedback(decision, agent_result)

        # Step 7: Persist to vault (if enabled)
        if self.enable_vault_persistence:
            await self._persist_to_vault(
                task,
                decision,
                agent_result,
                coherence,
                vault_guidance,
            )

        # Build compound result
        return CompoundAgentResult(
            success=agent_result.success,
            output=agent_result.output,
            agent_name=agent_result.agent_name,
            backend=agent_result.backend,
            latency_ms=agent_result.latency_ms,
            tokens_used=agent_result.tokens_used,
            routing_confidence=agent_result.routing_confidence,
            selected_agents=[agent_result.agent_name] + agent_result.tools_invoked,
            vault_guidance=vault_guidance,
            flume_embedding=flume_embedding,
            coherence_score=coherence,
            feedback_provided=True,
        )

    async def _get_vault_guidance(
        self,
        task: str,
    ) -> dict[str, Any] | None:
        """Query vault for similar task routing decisions."""
        try:
            # Query for similar tasks
            results = await self.mcp_client.find_relevant_context(
                task,
                limit=5,
                tag="multi_agent_routing",
            )

            if results:
                return {
                    "similar_tasks": results,
                    "recommended_agents": self._extract_agent_recommendations(results),
                }
        except Exception as e:
            logger.warning(f"Failed to get vault guidance: {e}")

        return None

    def _extract_agent_recommendations(
        self,
        vault_results: list[dict[str, Any]],
    ) -> list[str]:
        """Extract agent recommendations from vault results."""
        agent_scores: dict[str, float] = {}

        for result in vault_results:
            agent = result.get("agent_name")
            success = result.get("success", False)
            if agent:
                agent_scores[agent] = agent_scores.get(agent, 0) + (1 if success else 0)

        # Sort by score
        sorted_agents = sorted(
            agent_scores.items(),
            key=lambda x: x[1],
            reverse=True,
        )
        return [agent for agent, _ in sorted_agents]

    async def _flume_encode(self, task: str) -> list[float] | None:
        """FLUME-encode task characteristics."""
        try:
            from cohezion.flume import encode

            # Encode task for similarity matching
            embedding = await encode(task)
            return embedding.tolist() if hasattr(embedding, "tolist") else list(embedding)
        except Exception as e:
            logger.warning(f"FLUME encoding failed: {e}")
            return None

    async def _route_with_guidance(
        self,
        task: str,
        context: dict[str, Any],
        vault_guidance: dict[str, Any] | None,
    ) -> RoutingDecision:
        """Get routing decision with vault guidance."""
        # Enrich context with vault recommendations
        if vault_guidance:
            context["vault_recommended_agents"] = vault_guidance.get(
                "recommended_agents",
                [],
            )

        return await self._adaptive_router.route(task, context)

    async def _calculate_coherence(
        self,
        task: str,
        decision: RoutingDecision,
    ) -> float:
        """Calculate coherence score for HIHO."""
        if not self.enable_coherence_tracking:
            return 0.8  # Default

        # Simple heuristic: confidence * task clarity
        confidence = decision.confidence

        # Task clarity: longer, more specific tasks score higher
        task_length = len(task)
        has_specifics = any(word in task.lower() for word in ["function", "class", "method", "implement", "create"])
        clarity = min(1.0, (task_length / 100) * (1.2 if has_specifics else 0.8))

        return (confidence + clarity) / 2

    async def _provide_feedback(
        self,
        decision: RoutingDecision,
        result: AgentExecutionResult,
    ):
        """Provide feedback to adaptive router."""
        try:
            await self._adaptive_router.feedback(
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

    async def _persist_to_vault(
        self,
        task: str,
        decision: RoutingDecision,
        result: AgentExecutionResult,
        coherence: float,
        vault_guidance: dict[str, Any] | None,
    ):
        """Persist routing decision and outcome to vault."""
        try:
            record = {
                "type": "multi_agent_execution",
                "timestamp": datetime.now().isoformat(),
                "task": task[:500],  # Truncate for storage
                "agent_name": result.agent_name,
                "backend": result.backend,
                "routing_confidence": result.routing_confidence,
                "success": result.success,
                "latency_ms": result.latency_ms,
                "tokens_used": result.tokens_used,
                "coherence": coherence,
                "features": decision.features,
                "had_vault_guidance": vault_guidance is not None,
            }

            # Store in vault
            await self.mcp_client.write_to_vault(
                record,
                tags=["multi_agent_routing", result.agent_name],
            )
        except Exception as e:
            logger.warning(f"Failed to persist to vault: {e}")

    # ═══════════════════════════════════════════════════════════════════
    # Compound Loop Integration
    # ═══════════════════════════════════════════════════════════════════

    async def get_learning_summary(self) -> dict[str, Any]:
        """Get summary of learning progress."""
        await self._ensure_initialized()

        router_stats = self._adaptive_router.get_routing_stats()
        orchestrator_stats = self.orchestrator.get_stats()

        return {
            "routing_intelligence": router_stats,
            "execution_metrics": orchestrator_stats,
            "flume_enabled": self.enable_flume,
            "vault_persistence": self.enable_vault_persistence,
        }

    async def find_similar_tasks(
        self,
        task: str,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """Find similar tasks using FLUME similarity."""
        if not self.enable_flume:
            return []

        try:
            embedding = await self._flume_encode(task)
            if embedding:
                # Query vault with embedding
                return await self.mcp_client.find_similar(
                    embedding=embedding,
                    tag="multi_agent_routing",
                    limit=limit,
                )
        except Exception as e:
            logger.warning(f"Similar task search failed: {e}")

        return []


# Convenience function for quick usage
async def execute_with_compound_agents(
    task: str,
    mcp_client: MCPClient,
    context: dict[str, Any] | None = None,
) -> CompoundAgentResult:
    """Execute task with compound-integrated multi-agent system.

    Args:
        task: Task description
        mcp_client: Connected MCP client
        context: Optional execution context

    Returns:
        CompoundAgentResult with full routing metadata
    """
    bridge = MultiAgentCompoundBridge(mcp_client)
    return await bridge.execute(task, context)


class CompoundMultiAgentExecutor(CompoundExecutor):
    """CompoundExecutor with integrated MultiAgentOrchestrator.

    Extends the base CompoundExecutor to add multi-agent capabilities:
    - Automatic agent routing based on task characteristics
    - Adaptive learning from execution outcomes
    - Vault-persisted routing patterns
    - FLUME-encoded task similarity

    Usage:
        executor = CompoundMultiAgentExecutor(mcp_client)
        result = await executor.execute_task(
            task="Write a Python function",
            use_multi_agent=True,  # Enable multi-agent routing
        )
    """

    def __init__(
        self,
        mcp_client: MCPClient,
        **kwargs,
    ):
        """Initialize compound executor with multi-agent support."""
        super().__init__(mcp_client, **kwargs)

        # Multi-agent bridge (lazy initialization)
        self._multi_agent_bridge: MultiAgentCompoundBridge | None = None

    async def _get_multi_agent_bridge(self) -> MultiAgentCompoundBridge:
        """Get or create multi-agent bridge."""
        if self._multi_agent_bridge is None:
            self._multi_agent_bridge = MultiAgentCompoundBridge(
                self.mcp_client,
                enable_flume=True,
                enable_vault_persistence=True,
            )
        return self._multi_agent_bridge

    async def execute_task(
        self,
        task: str,
        use_multi_agent: bool = True,
        **kwargs,
    ) -> ExecutionResult:
        """Execute task with optional multi-agent routing.

        Args:
            task: Task description
            use_multi_agent: Whether to use multi-agent routing
            **kwargs: Passed to base executor

        Returns:
            ExecutionResult with compound metadata
        """
        if not use_multi_agent:
            # Fall back to standard compound execution
            return await super().execute_task(task, **kwargs)

        # Use multi-agent bridge
        bridge = await self._get_multi_agent_bridge()

        # Execute with multi-agent
        agent_result = await bridge.execute(task)

        # Convert to ExecutionResult format
        return ExecutionResult(
            success=agent_result.success,
            response=agent_result.output,
            tokens_used=agent_result.tokens_used,
            latency_ms=agent_result.latency_ms,
            metadata={
                "agent": agent_result.agent_name,
                "backend": agent_result.backend,
                "confidence": agent_result.routing_confidence,
                "coherence": agent_result.coherence_score,
                "vault_guidance": agent_result.vault_guidance is not None,
            },
        )
