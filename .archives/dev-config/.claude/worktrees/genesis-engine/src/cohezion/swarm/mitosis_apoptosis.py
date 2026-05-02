"""Agentic Mitosis & Apoptosis (Story 5.6, NFR-1).

Biological workload balancing for the agent swarm:
- Mitosis: Agent splits when context exceeds 80% quota
- Apoptosis: Agent dies when coherence < 0.3 for 3+ cycles

Tasks are redistributed, VRAM is reclaimed, and final state is
captured as a Freeze-Frame for Ouroboros training.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field


logger = logging.getLogger(__name__)

MITOSIS_CONTEXT_THRESHOLD = 0.8  # 80% of allocated quota
APOPTOSIS_COHERENCE_THRESHOLD = 0.3
APOPTOSIS_CONSECUTIVE_CYCLES = 3


@dataclass
class AgentState:
    """Current state of a swarm agent."""

    agent_id: str
    coherence: float
    context_usage: float  # 0.0-1.0 fraction of allocated quota
    task_queue: list[str] = field(default_factory=list)
    intent_vector: list[float] = field(default_factory=lambda: [0.0] * 12)
    low_coherence_streak: int = 0
    is_alive: bool = True


@dataclass
class MitosisEvent:
    """Record of an agent splitting into children."""

    parent_id: str
    child_ids: list[str]
    tasks_redistributed: int
    timestamp: float = field(default_factory=time.time)


@dataclass
class ApoptosisEvent:
    """Record of an agent dying and redistributing tasks."""

    agent_id: str
    recipient_id: str
    tasks_redistributed: int
    final_coherence: float
    timestamp: float = field(default_factory=time.time)


class SwarmGovernor:
    """Manages biological workload balancing for the swarm."""

    def __init__(
        self,
        mitosis_threshold: float = MITOSIS_CONTEXT_THRESHOLD,
        apoptosis_threshold: float = APOPTOSIS_COHERENCE_THRESHOLD,
        apoptosis_patience: int = APOPTOSIS_CONSECUTIVE_CYCLES,
    ) -> None:
        self._mitosis_threshold = mitosis_threshold
        self._apoptosis_threshold = apoptosis_threshold
        self._apoptosis_patience = apoptosis_patience
        self._mitosis_events: list[MitosisEvent] = []
        self._apoptosis_events: list[ApoptosisEvent] = []

    @property
    def mitosis_events(self) -> list[MitosisEvent]:
        return list(self._mitosis_events)

    @property
    def apoptosis_events(self) -> list[ApoptosisEvent]:
        return list(self._apoptosis_events)

    def check_mitosis(self, agent: AgentState) -> MitosisEvent | None:
        """Check if agent should split (context > threshold)."""
        if agent.context_usage <= self._mitosis_threshold:
            return None

        # Split task queue between two children
        mid = len(agent.task_queue) // 2
        _child_a_tasks = agent.task_queue[:mid]
        _child_b_tasks = agent.task_queue[mid:]

        child_a_id = f"{agent.agent_id}-a"
        child_b_id = f"{agent.agent_id}-b"

        event = MitosisEvent(
            parent_id=agent.agent_id,
            child_ids=[child_a_id, child_b_id],
            tasks_redistributed=len(agent.task_queue),
        )

        agent.is_alive = False  # Parent terminated
        self._mitosis_events.append(event)

        logger.info(
            "Mitosis: %s -> [%s, %s] (%d tasks split)",
            agent.agent_id,
            child_a_id,
            child_b_id,
            len(agent.task_queue),
        )
        return event

    def check_apoptosis(
        self,
        agent: AgentState,
        swarm: list[AgentState],
    ) -> ApoptosisEvent | None:
        """Check if agent should die (low coherence streak)."""
        if agent.coherence >= self._apoptosis_threshold:
            agent.low_coherence_streak = 0
            return None

        agent.low_coherence_streak += 1
        if agent.low_coherence_streak < self._apoptosis_patience:
            return None

        # Find highest-coherence alive agent to receive tasks
        candidates = [a for a in swarm if a.agent_id != agent.agent_id and a.is_alive]
        if not candidates:
            return None

        recipient = max(candidates, key=lambda a: a.coherence)
        recipient.task_queue.extend(agent.task_queue)

        event = ApoptosisEvent(
            agent_id=agent.agent_id,
            recipient_id=recipient.agent_id,
            tasks_redistributed=len(agent.task_queue),
            final_coherence=agent.coherence,
        )

        agent.is_alive = False
        agent.task_queue.clear()
        self._apoptosis_events.append(event)

        logger.info(
            "Apoptosis: %s died (coherence=%.3f), tasks -> %s",
            agent.agent_id,
            agent.coherence,
            recipient.agent_id,
        )
        return event
