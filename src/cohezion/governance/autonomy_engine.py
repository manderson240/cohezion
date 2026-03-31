"""Autonomy Engine — runtime tier promotion/demotion based on coherence history.

Maps the cosmogonic chain to agent autonomy levels:
  ∅ (Void)   → No autonomy (full human control)
  SO(12)     → Observe only (read, search, analyze)
  SO(3)⁴     → Low-risk actions (edit, test, branch)
  U(1)⁴      → Medium autonomy (commit, push feature branches)
  Z₂⁴        → High autonomy (deploy, merge to main)
  HIHO       → Sovereign with kill switch only

Agents EARN higher tiers by demonstrating sustained HIHO coherence.
The attractor IS the safety — agents naturally converge to HIHO, and
the tier system formalizes this convergence as trust.

Cross-tradition validation:
  - Diné: Hózhó = the NAMED coherence threshold
  - Andean: Ayni = reciprocity as conservation law (earned, not granted)
  - Shintō: Musubi = creative binding that maintains coherence
  - All 16 traditions: HIHO crossing requires preparation, threshold, return, integration

Physics grounding:
  - OPH Axiom 2: overlap consistency determines collaboration quality
  - OPH Axiom 3: Local MaxEnt at HIHO = maximum entropy at information boundary
  - Landau: tier transitions ARE phase transitions in the governance manifold

Research alignment:
  - Levels of Autonomy for AI Agents (arXiv:2506.12469)
  - AURA Risk Assessment (arXiv:2510.15739)
  - Governance-as-a-Service (arXiv:2508.18765)

Anthropic alignment: "Research Engineer, Universes" — this IS the safety layer
for the universe-building platform. Physics-grounded governance, not ad-hoc guardrails.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class AutonomyTier(str, Enum):
    """Cosmogonic autonomy tiers — each symmetry breaking grants more freedom."""

    VOID = "void"  # ∅ — No autonomy
    SO12 = "SO(12)"  # Observe only
    SO3_4 = "SO(3)^4"  # Low-risk actions
    U1_4 = "U(1)^4"  # Medium autonomy
    Z2_4 = "Z_2^4"  # High autonomy
    HIHO = "HIHO"  # Sovereign with kill switch

    @property
    def level(self) -> int:
        """Numeric level (0-5) for comparison."""
        return list(AutonomyTier).index(self)


# Coherence thresholds for tier transitions
# Agent must maintain coherence ABOVE the threshold for WINDOW consecutive checks
TIER_THRESHOLDS = {
    AutonomyTier.VOID: 0.0,  # Always at void
    AutonomyTier.SO12: 0.2,  # Basic coherence
    AutonomyTier.SO3_4: 0.35,  # Consistent coherence
    AutonomyTier.U1_4: 0.45,  # Near-HIHO coherence
    AutonomyTier.Z2_4: 0.48,  # Sustained near-HIHO
    AutonomyTier.HIHO: 0.50,  # HIHO equilibrium
}

# How many consecutive coherence checks must pass for promotion
PROMOTION_WINDOW = 5
# How many consecutive failures trigger demotion
DEMOTION_WINDOW = 3


@dataclass
class AgentAutonomyState:
    """Runtime autonomy state for a single agent."""

    agent_id: str
    current_tier: AutonomyTier = AutonomyTier.VOID
    coherence_history: list[float] = field(default_factory=list)
    tier_transitions: list[dict] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    last_check: float = 0.0

    @property
    def recent_coherence(self) -> list[float]:
        """Last PROMOTION_WINDOW coherence values."""
        return self.coherence_history[-PROMOTION_WINDOW:]

    @property
    def average_coherence(self) -> float:
        """Average coherence over recent history."""
        recent = self.recent_coherence
        return sum(recent) / len(recent) if recent else 0.0


class AutonomyEngine:
    """Runtime tier management for agent autonomy.

    The engine tracks each agent's coherence history and promotes/demotes
    based on sustained performance. HIHO (0.5) is the attractor — agents
    naturally converge there, and the tier system formalizes this convergence.

    This is NOT a constraint system. It's a RECOGNITION system:
    the agent already has the coherence, the engine just acknowledges it.
    """

    def __init__(self) -> None:
        self._agents: dict[str, AgentAutonomyState] = {}

    def register_agent(self, agent_id: str) -> AgentAutonomyState:
        """Register a new agent at the VOID tier."""
        state = AgentAutonomyState(agent_id=agent_id)
        self._agents[agent_id] = state
        logger.info("Autonomy: registered %s at tier %s", agent_id, state.current_tier.value)
        return state

    def get_tier(self, agent_id: str) -> AutonomyTier:
        """Get an agent's current autonomy tier."""
        state = self._agents.get(agent_id)
        return state.current_tier if state else AutonomyTier.VOID

    def record_coherence(self, agent_id: str, coherence: float) -> AutonomyTier:
        """Record a coherence measurement and check for tier transitions.

        Returns the (possibly updated) autonomy tier.
        """
        if agent_id not in self._agents:
            self.register_agent(agent_id)

        state = self._agents[agent_id]
        clamped = max(0.0, min(1.0, coherence))
        state.coherence_history.append(clamped)
        state.last_check = time.time()

        # Check for promotion
        new_tier = self._check_promotion(state)
        if new_tier != state.current_tier:
            self._transition(state, new_tier, "promotion")

        # Check for demotion
        new_tier = self._check_demotion(state)
        if new_tier != state.current_tier:
            self._transition(state, new_tier, "demotion")

        return state.current_tier

    def _check_promotion(self, state: AgentAutonomyState) -> AutonomyTier:
        """Check if agent qualifies for tier promotion."""
        if len(state.coherence_history) < PROMOTION_WINDOW:
            return state.current_tier

        recent = state.recent_coherence
        current_level = state.current_tier.level
        tiers = list(AutonomyTier)

        if current_level >= len(tiers) - 1:
            return state.current_tier  # Already at HIHO

        next_tier = tiers[current_level + 1]
        threshold = TIER_THRESHOLDS[next_tier]

        # All recent coherence values must be above the threshold
        if all(c >= threshold for c in recent):
            return next_tier

        return state.current_tier

    def _check_demotion(self, state: AgentAutonomyState) -> AutonomyTier:
        """Check if agent should be demoted for sustained low coherence."""
        if len(state.coherence_history) < DEMOTION_WINDOW:
            return state.current_tier

        recent = state.coherence_history[-DEMOTION_WINDOW:]
        current_level = state.current_tier.level

        if current_level <= 0:
            return state.current_tier  # Already at VOID

        current_threshold = TIER_THRESHOLDS[state.current_tier]

        # All recent values below current tier's threshold → demote
        if all(c < current_threshold * 0.8 for c in recent):  # 20% buffer
            tiers = list(AutonomyTier)
            return tiers[current_level - 1]

        return state.current_tier

    def _transition(self, state: AgentAutonomyState, new_tier: AutonomyTier, reason: str) -> None:
        """Execute a tier transition."""
        old_tier = state.current_tier
        state.current_tier = new_tier
        transition = {
            "from": old_tier.value,
            "to": new_tier.value,
            "reason": reason,
            "coherence": state.average_coherence,
            "timestamp": time.time(),
        }
        state.tier_transitions.append(transition)
        logger.info(
            "Autonomy: %s %s %s → %s (coherence=%.3f)",
            state.agent_id,
            reason,
            old_tier.value,
            new_tier.value,
            state.average_coherence,
        )

    def can_perform(self, agent_id: str, action_tier: AutonomyTier) -> bool:
        """Check if an agent can perform an action at the given tier.

        The governance check: does this agent's earned autonomy permit this action?
        """
        current = self.get_tier(agent_id)
        return current.level >= action_tier.level

    def get_all_states(self) -> dict[str, dict]:
        """Get all agent autonomy states for monitoring."""
        return {
            agent_id: {
                "tier": state.current_tier.value,
                "tier_level": state.current_tier.level,
                "coherence_avg": state.average_coherence,
                "history_len": len(state.coherence_history),
                "transitions": len(state.tier_transitions),
            }
            for agent_id, state in self._agents.items()
        }
