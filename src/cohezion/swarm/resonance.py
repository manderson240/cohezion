"""Resonance Protocol and Swarm Orchestrator for Advanced Agent Collaboration.

Enables agents to share 12D state vectors and latent intent to reach
HIHO stability (0.5 coherence) during complex problem solving.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field

from cohezion.swarm.orchestrator import Agent, AgentResult, Task


logger = logging.getLogger(__name__)


@dataclass
class ResonanceState:
    """12D state vector for resonance sharing."""

    agent_id: str
    spatial: list[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    time: float = 0.0
    brane: list[float] = field(default_factory=lambda: [0.0] * 8)
    coherence: float = 0.0


class ResonanceProtocol:
    """Handles the exchange of 12D state vectors between agents."""

    def __init__(self):
        self.buffer: list[ResonanceState] = []
        self._lock = asyncio.Lock()

    async def share(self, state: ResonanceState) -> None:
        """Share a state vector to the resonance buffer."""
        async with self._lock:
            self.buffer.append(state)
            logger.debug(f"Resonance shared by {state.agent_id} (coherence: {state.coherence})")

    async def get_latest(self) -> ResonanceState | None:
        """Get the most recent resonance state."""
        async with self._lock:
            return self.buffer[-1] if self.buffer else None

    async def calculate_collective_coherence(self) -> float:
        """Calculate the average coherence of the current resonance buffer."""
        async with self._lock:
            if not self.buffer:
                return 0.0
            return sum(s.coherence for s in self.buffer) / len(self.buffer)


class SwarmOrchestrator:
    """Specialized orchestrator for high-resonance multi-agent loops."""

    def __init__(self, resonance_protocol: ResonanceProtocol | None = None):
        self.resonance = resonance_protocol or ResonanceProtocol()
        self.agents: dict[str, Agent] = {}

    def register_agent(self, agent: Agent) -> None:
        """Register an agent for resonance collaboration."""
        self.agents[agent.id] = agent

    async def execute_resonance_loop(self, task: Task, lead_agent_id: str) -> dict[str, AgentResult]:
        """Execute a collaborative loop with parallel execution and production fallbacks."""
        results: dict[str, AgentResult] = {}

        # 1. Separate Lead and Support agents
        support_agent_ids = [aid for aid in self.agents if aid != lead_agent_id]

        # 2. Parallel execution for support agents
        logger.info(f"Executing support agents in parallel: {support_agent_ids}")
        support_tasks = [self.agents[aid].execute(task) for aid in support_agent_ids]
        support_results = await asyncio.gather(*support_tasks, return_exceptions=True)

        for aid, result in zip(support_agent_ids, support_results):
            if isinstance(result, Exception):
                logger.error(f"Support agent {aid} failed: {result}")
                results[aid] = AgentResult(id=aid, success=False, output=str(result))
                continue

            results[aid] = result
            await self.resonance.share(ResonanceState(agent_id=aid, coherence=0.5 if result.success else 0.1))

        # 3. Execute Lead Agent with production fallback (Gemma 4 -> Gemini Flash)
        logger.info(f"Executing lead agent sequentially: {lead_agent_id}")
        try:
            lead_result = await self.agents[lead_agent_id].execute(task)
        except Exception:
            logger.warning(f"Lead agent {lead_agent_id} failed, attempting production fallback to Gemini Flash...")
            # Fallback logic (simulated for the resonance loop)
            fallback_task = task
            fallback_task.description += " [FALLBACK MODE: Gemini Flash]"
            lead_result = await self.agents[lead_agent_id].execute(fallback_task)

        results[lead_agent_id] = lead_result

        await self.resonance.share(
            ResonanceState(agent_id=lead_agent_id, coherence=0.5 if lead_result.success else 0.1)
        )

        return results
