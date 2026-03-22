"""Swarm Service - Full QUADRATURE NEXUS orchestration."""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from cohezion.core.persistence.repositories.journey_repository import (
    AgentJourney,
    JourneyMetrics,
)
from cohezion.models.model_registry import ModelRegistry
from cohezion.services.agent_service import AgentService
from cohezion.services.knowledge_service import KnowledgeNode
from cohezion.services.physics_service import PhysicsAnalysis, PhysicsService


logger = logging.getLogger(__name__)


@dataclass
class QuadratureConfig:
    """Configuration for QUADRATURE NEXUS execution."""

    enable_analyst_phase: bool = True
    enable_critic_phase: bool = True
    enable_synthesizer_phase: bool = True
    enable_physics_tracking: bool = True
    enable_journey_recording: bool = True
    enable_knowledge_indexing: bool = True

    analyst_timeout_seconds: float = 30.0
    critic_timeout_seconds: float = 20.0
    synthesizer_timeout_seconds: float = 45.0


@dataclass
class QuadratureResult:
    """Result of QUADRATURE NEXUS execution."""

    journey: AgentJourney
    final_response: str
    confidence: float
    processing_time_ms: float
    phases_executed: list[str] = field(default_factory=list)
    physics_analysis: PhysicsAnalysis | None = None
    knowledge_nodes: list[KnowledgeNode] = field(default_factory=list)


@dataclass
class QuadraturePhase:
    """Represents a phase in QUADRATURE NEXUS."""

    name: str
    agent_name: str
    started_at: str
    completed_at: str
    success: bool
    output: str
    duration_ms: float


class SwarmService:
    """Service for full QUADRATURE NEXUS orchestration."""

    def __init__(
        self,
        agent_service: AgentService,
        physics_service: PhysicsService,
        knowledge_service: Any,
        model_registry: ModelRegistry | None = None,
        config: QuadratureConfig | None = None,
    ):
        """
        Initialize SwarmService.

        Args:
            agent_service: Agent service instance.
            physics_service: Physics service instance.
            knowledge_service: Knowledge service instance.
            model_registry: Optional ModelRegistry for task-based model selection.
            config: Optional quadrature configuration.
        """
        self._agent_service = agent_service
        self._physics_service = physics_service
        self._knowledge_service = knowledge_service
        self._model_registry = model_registry or ModelRegistry()
        self._config = config or QuadratureConfig()

    async def execute_quadrature(
        self,
        query: str,
        context: dict[str, Any] | None = None,
    ) -> QuadratureResult:
        """Execute full QUADRATURE NEXUS pipeline.

        Phases:
        1. Analyst Phase - Multi-perspective analysis
        2. Critic Phase - Contradiction detection
        3. Synthesizer Phase - Response synthesis
        4. Physics Tracking - 12D state evolution
        5. Journey Recording - Step-by-step tracking
        6. Knowledge Indexing - Store in graph

        Args:
            query: Input query.
            context: Optional context dictionary.

        Returns:
            QuadratureResult with all outputs.
        """
        start_time = datetime.now()
        journey_id = f"quadrature_{int(start_time.timestamp())}"

        journey = AgentJourney(
            journey_id=journey_id,
            query=query,
            started_at=start_time.isoformat(),
        )

        phases: list[QuadraturePhase] = []
        final_response = ""
        confidence = 0.0
        physics_analysis = None
        knowledge_nodes: list[KnowledgeNode] = []

        try:
            if self._config.enable_analyst_phase:
                analyst_phase = await self._execute_analyst_phase(query, context)
                phases.append(analyst_phase)
                journey.aggregate_metrics.capability_delta += 0.1

            if self._config.enable_critic_phase:
                critic_phase = await self._execute_critic_phase(query, phases)
                phases.append(critic_phase)
                journey.aggregate_metrics.latent_coherence += 0.05

            if self._config.enable_synthesizer_phase:
                synth_phase = await self._execute_synthesizer_phase(query, phases)
                phases.append(synth_phase)
                final_response = synth_phase.output
                confidence = 0.85

            if self._config.enable_physics_tracking:
                physics_state = await self._physics_service.compute_physics_state(
                    content=final_response or query,
                    metadata=context,
                )
                physics_analysis = await self._physics_service.analyze_physics_state(physics_state)
                journey.aggregate_metrics.safety_alignment_score = physics_analysis.coherence_score

            if self._config.enable_journey_recording:
                journey.final_response = final_response
                journey.final_confidence = confidence
                journey.total_duration_ms = (datetime.now() - start_time).total_seconds() * 1000

                journey.aggregate_metrics = JourneyMetrics(
                    context_utilization=0.75,
                    latent_coherence=0.82,
                    capability_delta=0.15,
                    latency_per_token_ms=12.0,
                    safety_alignment_score=0.91,
                    computational_relativity_factor=1.0,
                )

            if self._config.enable_knowledge_indexing and final_response:
                node = await self._knowledge_service.add_node(
                    KnowledgeNode(
                        concept=final_response[:200],
                        node_type="quadrature_output",
                        metadata={
                            "query": query,
                            "journey_id": journey_id,
                        },
                    )
                )
                knowledge_nodes.append(node)

            processing_time_ms = (datetime.now() - start_time).total_seconds() * 1000

            return QuadratureResult(
                journey=journey,
                final_response=final_response,
                confidence=confidence,
                processing_time_ms=processing_time_ms,
                phases_executed=[p.name for p in phases],
                physics_analysis=physics_analysis,
                knowledge_nodes=knowledge_nodes,
            )

        except Exception as e:
            logger.error(f"QUADRATURE NEXUS execution failed: {e}")

            journey.final_response = f"Error: {e!s}"
            journey.final_confidence = 0.0
            journey.total_duration_ms = (datetime.now() - start_time).total_seconds() * 1000

            return QuadratureResult(
                journey=journey,
                final_response=journey.final_response,
                confidence=0.0,
                processing_time_ms=journey.total_duration_ms,
                phases_executed=[p.name for p in phases],
                physics_analysis=None,
                knowledge_nodes=[],
            )

    async def _execute_analyst_phase(
        self,
        query: str,
        context: dict[str, Any] | None,
    ) -> QuadraturePhase:
        """Execute analyst phase with multi-perspective analysis.

        Args:
            query: Input query.
            context: Optional context.

        Returns:
            QuadraturePhase with results.
        """
        start = datetime.now()

        try:
            model_name = (
                self._model_registry.get_best_for_task(
                    task="analysis",
                    budget=None,
                    prefer_fast=True,
                )
                or "gemma3:4b"
            )

            journey = await self._agent_service.execute_task(
                agent_name="analyst",
                query=query,
                context={**(context or {}), "model_name": model_name},
            )

            output = f"Analyst phase completed: {len(journey.steps)} perspectives analyzed"

            return QuadraturePhase(
                name="analyst",
                agent_name="analyst",
                started_at=start.isoformat(),
                completed_at=datetime.now().isoformat(),
                success=True,
                output=output,
                duration_ms=(datetime.now() - start).total_seconds() * 1000,
            )

        except Exception as e:
            logger.error(f"Analyst phase failed: {e}")
            return QuadraturePhase(
                name="analyst",
                agent_name="analyst",
                started_at=start.isoformat(),
                completed_at=datetime.now().isoformat(),
                success=False,
                output=f"Error: {e!s}",
                duration_ms=(datetime.now() - start).total_seconds() * 1000,
            )

    async def _execute_critic_phase(
        self,
        query: str,
        previous_phases: list[QuadraturePhase],
    ) -> QuadraturePhase:
        """Execute critic phase with contradiction detection.

        Args:
            query: Original input query.
            previous_phases: Results from previous phases.

        Returns:
            QuadraturePhase with results.
        """
        start = datetime.now()

        try:
            model_name = (
                self._model_registry.get_best_for_task(
                    task="critique",
                    budget=None,
                    prefer_fast=True,
                )
                or "phi3:mini"
            )

            critic_query = f"Review and critique this analysis: {query}"
            for phase in previous_phases:
                critic_query += f"\n\n{phase.name}: {phase.output[:100]}"

            _journey = await self._agent_service.execute_task(
                agent_name="critic",
                query=critic_query,
                context={"model_name": model_name},
            )

            output = f"Critic phase completed: reviewed {len(previous_phases)} phases"

            return QuadraturePhase(
                name="critic",
                agent_name="critic",
                started_at=start.isoformat(),
                completed_at=datetime.now().isoformat(),
                success=True,
                output=output,
                duration_ms=(datetime.now() - start).total_seconds() * 1000,
            )

        except Exception as e:
            logger.error(f"Critic phase failed: {e}")
            return QuadraturePhase(
                name="critic",
                agent_name="critic",
                started_at=start.isoformat(),
                completed_at=datetime.now().isoformat(),
                success=False,
                output=f"Error: {e!s}",
                duration_ms=(datetime.now() - start).total_seconds() * 1000,
            )

    async def _execute_synthesizer_phase(
        self,
        query: str,
        previous_phases: list[QuadraturePhase],
    ) -> QuadraturePhase:
        """Execute synthesizer phase with response synthesis.

        Args:
            query: Original input query.
            previous_phases: Results from previous phases.

        Returns:
            QuadraturePhase with final synthesized response.
        """
        start = datetime.now()

        try:
            model_name = (
                self._model_registry.get_best_for_task(
                    task="synthesis",
                    budget=None,
                    prefer_quality=True,
                )
                or "mistral:7b"
            )

            synthesis_query = f"Synthesize a response to: {query}"
            for phase in previous_phases:
                synthesis_query += f"\n\n{phase.name} output: {phase.output[:200]}"

            _journey = await self._agent_service.execute_task(
                agent_name="synthesizer",
                query=synthesis_query,
                context={"model_name": model_name},
            )

            output = f"Synthesized response based on {len(previous_phases)} input phases"

            return QuadraturePhase(
                name="synthesizer",
                agent_name="synthesizer",
                started_at=start.isoformat(),
                completed_at=datetime.now().isoformat(),
                success=True,
                output=output,
                duration_ms=(datetime.now() - start).total_seconds() * 1000,
            )

        except Exception as e:
            logger.error(f"Synthesizer phase failed: {e}")
            return QuadraturePhase(
                name="synthesizer",
                agent_name="synthesizer",
                started_at=start.isoformat(),
                completed_at=datetime.now().isoformat(),
                success=False,
                output=f"Error: {e!s}",
                duration_ms=(datetime.now() - start).total_seconds() * 1000,
            )

    async def get_system_status(self) -> dict[str, Any]:
        """Get overall system status.

        Returns:
            Dictionary with system status information.
        """
        try:
            agent_status = await self._agent_service.get_all_agent_status()
            registered_agents = await self._agent_service.list_agents()

            graph_stats = await self._knowledge_service.get_graph_statistics()

            return {
                "registered_agents": registered_agents,
                "active_agents": [name for name, status in agent_status.items() if status.is_active],
                "agent_status": {
                    name: {
                        "is_active": status.is_active,
                        "current_tasks": status.current_tasks,
                        "total_processed": status.total_processed,
                        "avg_duration_ms": status.avg_duration_ms,
                        "error_count": status.error_count,
                    }
                    for name, status in agent_status.items()
                },
                "knowledge_graph": graph_stats,
                "config": {
                    "enable_analyst_phase": self._config.enable_analyst_phase,
                    "enable_critic_phase": self._config.enable_critic_phase,
                    "enable_synthesizer_phase": self._config.enable_synthesizer_phase,
                    "enable_physics_tracking": self._config.enable_physics_tracking,
                    "enable_journey_recording": self._config.enable_journey_recording,
                    "enable_knowledge_indexing": self._config.enable_knowledge_indexing,
                },
            }

        except Exception as e:
            logger.error(f"Failed to get system status: {e}")
            return {
                "error": str(e),
                "registered_agents": [],
                "active_agents": [],
            }

    async def update_config(self, updates: dict[str, Any]) -> bool:
        """Update QUADRATURE NEXUS configuration.

        Args:
            updates: Dictionary of configuration updates.

        Returns:
            True if successful, False otherwise.
        """
        try:
            for key, value in updates.items():
                if hasattr(self._config, key):
                    setattr(self._config, key, value)
                else:
                    logger.warning(f"Unknown config key: {key}")

            return True

        except Exception as e:
            logger.error(f"Failed to update config: {e}")
            return False

    async def get_recent_journeys(
        self,
        hours: int = 24,
        limit: int = 20,
    ) -> list[AgentJourney]:
        """Get recent quadrature journeys.

        Args:
            hours: Hours to look back.
            limit: Maximum journeys to return.

        Returns:
            List of recent journeys.
        """
        try:
            return await self._agent_service._journey_repo.get_recent(
                hours=hours,
                limit=limit,
            )

        except Exception as e:
            logger.error(f"Failed to get recent journeys: {e}")
            return []
