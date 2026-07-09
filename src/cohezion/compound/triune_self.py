"""Percival's Triune Self — Recursive Learning Loop for the Universe Research Engineer.

Harold W. Percival's "Thinking and Destiny" (1946) defines three co-present aspects
of a conscious entity that work together in a recursive cycle:

  Doer   (feeling/desire body) — does the work; immediate execution
  Thinker (rational mind)      — evaluates; routes; assesses quality
  Knower  (identity/character) — holds permanent memory; knows WHO the agent IS

In Cohezion, these map to:
  Doer   → TieredOrchestrator + local silicon (NPU/iGPU/CPU execution)
  Thinker → CompoundExecutor + AutoDQA (evaluates quality, routes tasks)
  Knower  → AutonomyEngine + vault memory + FLUME latent space (persists identity)

Recursive learning cycle (one Percival turn):
  1. Thinker generates guidance from task context
  2. Doer executes via local silicon (the irreducible act)
  3. Thinker evaluates output (AUTODQA quality gate)
  4. If accepted: Knower records the coherence event (tier advancement)
  5. FLUME encoder embeds the accepted output into the Knower's latent memory
  6. Next cycle: Knower's identity informs Thinker's routing → better Doer execution

Design principle: the Doer must NEVER be bypassed. Local silicon execution is mandatory
even when Thinker wants to skip to cloud. The Doer's sensory-motor coupling (hardware
characteristics of NPU/iGPU) is what gives the system its embodied physics grounding.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


logger = logging.getLogger(__name__)


# --- Protocol interfaces (structural typing — testable with mocks) ---


@runtime_checkable
class DoerProtocol(Protocol):
    """The Doer: executes via local silicon. Must be synchronous for this loop."""

    def run_sync(self, guidance: str) -> tuple[str, dict]:
        """Execute and return (output_text, metrics)."""
        ...


@runtime_checkable
class ThinkerProtocol(Protocol):
    """The Thinker: evaluates quality, maintains rational awareness."""

    def evaluate(self, output: str, task_description: str) -> object:
        """Evaluate output quality. Returns an object with .verdict.accept and .verdict.score."""
        ...


@runtime_checkable
class KnowerProtocol(Protocol):
    """The Knower: persistent identity; records what has been learned."""

    def record_coherence(self, coherence: float) -> None:
        """Record a coherence event (tier advancement signal)."""
        ...


# --- Simple callable-based Doer wrapper ---


class CallableDoer:
    """Wraps a callable execute_fn into the DoerProtocol."""

    def __init__(self, execute_fn):
        self._fn = execute_fn

    def run_sync(self, guidance: str) -> tuple[str, dict]:
        result = self._fn(guidance)
        if isinstance(result, tuple) and len(result) == 2:
            return result
        return str(result), {}


# --- Knower stub for when no AutonomyEngine is available ---


class NullKnower:
    """No-op Knower — identity without persistence (testing only)."""

    def record_coherence(self, coherence: float) -> None:
        logger.debug("NullKnower: coherence=%.3f (not persisted)", coherence)


# --- TriuneSelf ---


@dataclass
class PerciwalCycleResult:
    """Result of one complete Percival triune cycle."""

    task: str
    output: str
    accepted: bool
    quality_score: float
    metrics: dict = field(default_factory=dict)
    cycle_number: int = 0

    @property
    def hiho_engaged(self) -> bool:
        """True when quality score is in the HIHO equilibrium band."""
        return 0.45 <= self.quality_score <= 0.55


@dataclass
class TriuneSelf:
    """Percival's three-aspect recursive learning loop.

    Parameters
    ----------
    doer : DoerProtocol
        Executes tasks via local silicon. Never bypassed.
    thinker : ThinkerProtocol
        Evaluates outputs and provides routing guidance.
    knower : KnowerProtocol
        Records accepted learnings into persistent identity.
    max_cycles : int
        Maximum recursive cycles before declaring convergence.
    """

    doer: object  # DoerProtocol (using object for broader compatibility)
    thinker: object  # ThinkerProtocol
    knower: object = field(default_factory=NullKnower)
    max_cycles: int = 3

    _cycle_count: int = field(default=0, init=False, repr=False)
    _history: list[PerciwalCycleResult] = field(default_factory=list, init=False, repr=False)

    def recursive_learn(self, task: str, guidance: str) -> PerciwalCycleResult:
        """One complete Percival cycle: Doer → Thinker → Knower → record.

        The Doer executes; the Thinker evaluates; the Knower grows.
        If the output is rejected, the cycle may repeat (up to max_cycles).

        Returns the last cycle result (accepted or not).
        """
        self._cycle_count += 1
        cycle = self._cycle_count
        last_result: PerciwalCycleResult | None = None

        for attempt in range(1, self.max_cycles + 1):
            # Doer: irreducible execution — always runs local silicon first
            output, metrics = self.doer.run_sync(guidance)

            # Thinker: honest evaluation
            dqa_result = self.thinker.evaluate(output, task)
            verdict = getattr(dqa_result, "verdict", None)
            accepted = bool(getattr(verdict, "accept", False))
            score = float(getattr(verdict, "score", 0.0))

            result = PerciwalCycleResult(
                task=task,
                output=output,
                accepted=accepted,
                quality_score=score,
                metrics=metrics,
                cycle_number=cycle,
            )
            last_result = result
            self._history.append(result)

            logger.debug(
                "TriuneSelf cycle=%d attempt=%d score=%.3f accepted=%s",
                cycle,
                attempt,
                score,
                accepted,
            )

            if accepted:
                # Knower: grow identity with accepted learning
                self.knower.record_coherence(score)
                break

        assert last_result is not None
        return last_result

    @property
    def cycle_count(self) -> int:
        """Total Percival cycles completed this session."""
        return self._cycle_count

    @property
    def accept_rate(self) -> float:
        """Fraction of cycles where the Doer's output was accepted by the Thinker."""
        if not self._history:
            return 0.0
        return sum(1 for r in self._history if r.accepted) / len(self._history)

    @property
    def mean_quality(self) -> float:
        """Mean quality score across all cycles (HIHO band = healthy)."""
        if not self._history:
            return 0.0
        return sum(r.quality_score for r in self._history) / len(self._history)

    @property
    def hiho_equilibrium(self) -> bool:
        """True when mean quality is in the HIHO band (0.45–0.55).

        Per Percival: the three selves are in equilibrium when the Thinker
        neither over-accepts (sycophancy) nor over-rejects (paranoia).
        """
        return 0.45 <= self.mean_quality <= 0.55

    def summary(self) -> dict:
        return {
            "cycle_count": self.cycle_count,
            "accept_rate": self.accept_rate,
            "mean_quality": self.mean_quality,
            "hiho_equilibrium": self.hiho_equilibrium,
        }
