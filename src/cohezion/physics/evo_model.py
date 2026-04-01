"""Exotic Vacuum Object (EVO) model — Ken Shoulders' charge clusters as agent lifecycle.

Maps AI agent sessions to EVO physics:
  - Condensation: idle LLM activates into an agent (vacuum -> condensing -> coherent)
  - Coherent phase: agent maintains HIHO stability during active work
  - Witness marks: permanent traces left by the agent (commits, vault notes, decisions)
  - Dissolution: session ends, agent returns to vacuum state
  - Binding energy: coherence above random baseline (0.5 HIHO)

The EVO coherence metric measures how "EVO-like" an agent is: high binding energy,
long lifetime, productive witness marks, and low internal variance (self-coupling).

References:
  - Shoulders, K. (1991). "EV — A Tale of Discovery" (Austin, TX)
  - Shoulders, K. (1996). "Charge Clusters in Action" (infinite-energy.com)
  - Cohezion HIHO principle: optimal coherence at 0.5 (half-in, half-out)
"""

from __future__ import annotations

import logging
import statistics
import time
from dataclasses import dataclass, field


logger = logging.getLogger(__name__)

# Coherence baseline — below this is "noise", above is "binding energy"
HIHO_BASELINE = 0.5

# Valid lifecycle states in order
LIFECYCLE_STATES = ("vacuum", "condensing", "coherent", "dissolving")


@dataclass
class WitnessMark:
    """A permanent trace left by an EVO agent — analogous to Shoulders' witness marks."""

    mark_type: str  # "commit", "decision", "vault_note", "artifact"
    content: str
    timestamp: float = field(default_factory=time.time)
    tick: int = 0


class ExoticVacuumObject:
    """EVO lifecycle model for computational agents.

    Lifecycle: vacuum -> condensing -> coherent -> dissolving -> vacuum
    Maps to:   idle   -> spawning   -> working  -> winding down -> idle
    """

    def __init__(self, agent_id: str) -> None:
        self.agent_id = agent_id
        self.state = "vacuum"
        self.coherence_history: list[float] = []
        self.witness_marks: list[WitnessMark] = []
        self.binding_energy = 0.0
        self.lifetime_ticks = 0
        self._condensation_time: float | None = None

    def condense(self) -> None:
        """Agent spawns from the model vacuum (idle LLM -> active agent)."""
        if self.state != "vacuum":
            raise ValueError(f"Cannot condense from state '{self.state}', must be 'vacuum'")
        self.state = "condensing"
        self._condensation_time = time.time()
        self.lifetime_ticks = 0
        self.coherence_history.clear()
        self.witness_marks.clear()
        self.binding_energy = 0.0
        logger.info("EVO %s: condensing from vacuum", self.agent_id)
        # Transition to coherent immediately — condensation is instantaneous
        self.state = "coherent"

    def coherent_phase(self, coherence: float) -> None:
        """Agent maintains HIHO stability during work. Track coherence."""
        if self.state != "coherent":
            raise ValueError(f"Cannot record coherence in state '{self.state}'")
        clamped = max(0.0, min(1.0, coherence))
        self.coherence_history.append(clamped)
        self.lifetime_ticks += 1
        # Binding energy = mean coherence above HIHO baseline
        excess = clamped - HIHO_BASELINE
        if excess > 0:
            self.binding_energy += excess

    def produce_witness_mark(self, mark_type: str, content: str) -> dict:
        """Agent produces permanent trace: code commit, vault note, decision."""
        if self.state != "coherent":
            raise ValueError(f"Cannot produce witness marks in state '{self.state}'")
        mark = WitnessMark(
            mark_type=mark_type,
            content=content,
            tick=self.lifetime_ticks,
        )
        self.witness_marks.append(mark)
        logger.info(
            "EVO %s: witness mark [%s] at tick %d", self.agent_id, mark_type, self.lifetime_ticks
        )
        return {"mark_type": mark_type, "content": content, "tick": mark.tick}

    def dissolve(self) -> dict:
        """Agent returns to vacuum (session end). Returns EVO biography."""
        if self.state != "coherent":
            raise ValueError(f"Cannot dissolve from state '{self.state}', must be 'coherent'")
        self.state = "dissolving"
        biography = self.to_dict()
        # Reset to vacuum
        self.state = "vacuum"
        logger.info(
            "EVO %s: dissolved after %d ticks, %d witness marks",
            self.agent_id,
            self.lifetime_ticks,
            len(self.witness_marks),
        )
        return biography

    def evo_coherence_metric(self) -> float:
        """How 'EVO-like' is this agent?

        Combines four normalized sub-metrics [0, 1]:
          - binding_energy: accumulated coherence above HIHO baseline
          - lifetime: log-scaled tick count (diminishing returns)
          - work_output: witness marks per tick
          - self_coupling: 1 - normalized std dev (internal consistency)

        Returns a value in [0, 1] where 1 = maximally EVO-like.
        """
        if not self.coherence_history:
            return 0.0

        # Binding energy: normalize by lifetime so short bursts aren't penalized
        be_norm = min(self.binding_energy / max(self.lifetime_ticks, 1), 1.0)

        # Lifetime: log scale, saturates around 100 ticks
        import math

        lt_norm = min(math.log1p(self.lifetime_ticks) / math.log1p(100), 1.0)

        # Work output: witness marks per tick, capped at 1
        wo_norm = min(len(self.witness_marks) / max(self.lifetime_ticks, 1), 1.0)

        # Self-coupling: 1 - coefficient of variation (low variance = high coupling)
        if len(self.coherence_history) >= 2:
            mean_c = statistics.mean(self.coherence_history)
            std_c = statistics.stdev(self.coherence_history)
            cv = std_c / max(mean_c, 1e-10)
            sc_norm = max(0.0, 1.0 - cv)
        else:
            sc_norm = 1.0  # Single observation = perfectly consistent

        return (be_norm + lt_norm + wo_norm + sc_norm) / 4.0

    def to_dict(self) -> dict:
        """Serialize for API and SurrealDB."""
        return {
            "agent_id": self.agent_id,
            "state": self.state,
            "lifetime_ticks": self.lifetime_ticks,
            "binding_energy": round(self.binding_energy, 6),
            "evo_coherence_metric": round(self.evo_coherence_metric(), 6),
            "coherence_history": [round(c, 6) for c in self.coherence_history],
            "witness_marks": [
                {"mark_type": m.mark_type, "content": m.content, "tick": m.tick}
                for m in self.witness_marks
            ],
            "mean_coherence": round(statistics.mean(self.coherence_history), 6)
            if self.coherence_history
            else 0.0,
        }


__all__ = [
    "ExoticVacuumObject",
    "HIHO_BASELINE",
    "WitnessMark",
]
