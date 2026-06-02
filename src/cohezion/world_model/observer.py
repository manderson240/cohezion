"""Observer — the unifying abstraction behind cohezion's active-inference machinery.

Donald Hoffman's interface theory (and the Jesse Michels interview that prompted this) names a
formal structure for an observer:

  * an observer is a **matrix of outcome states** with Markovian dynamics ("conscious agent"),
  * a space of observers tied together by **"the no-surprise logic of all observation"**,
  * **recursive trace logic** that nests observers,
  * composing into **multi-scale collective intelligence** (he cites Levin and planaria).

Cohezion already built each of those pieces separately. ``Observer`` is the type that composes
them into Hoffman's structure — and, because it nests recursively, the same construction is
Levin's Multi-Scale Competency Architecture: a collective at scale N is itself an observer at
scale N+1, with a wider cognitive light cone.

    Observer = TransitionController         # the matrix of outcome states (Markov)
             + SurpriseRouter               # the "no-surprise logic" (active inference)
             + children: list[Observer]     # recursive trace / Levin nesting
             + (optional) SurpriseActionGate # QuadratureNexus consensus on risky actions

Nothing here is new physics or metaphysics — it is a thin composition of existing, tested
primitives. The speculative layer of the source material (consciousness-as-fundamental,
"hacking the headset", UAP) is deliberately *not* encoded; this is the engineering core only.

The cognitive light cone widens with the size of the nested collective: a lone agent sees a
narrow horizon; a percolated collective of N agents spans a wider one (R_c ∝ √(D·τ·N)). The
collective's attention follows the **most-surprised** subsystem — where prediction has broken
down — which is the multi-scale form of the same epistemic-value rule the single-scale router uses.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from math import sqrt

from cohezion.physics.bioelectric_model import CognitiveLightCone
from cohezion.world_model.surprise_router import SurpriseDecision, SurpriseRouter


__all__ = ["Observer"]


@dataclass
class Observer:
    """A Hoffman-style observer: a Markov state-matrix observed under no-surprise logic,
    recursively nestable into multi-scale collectives.

    Parameters
    ----------
    name:
        Identifier for this observer (used in the cognitive light cone agent set).
    state_matrix:
        The :class:`TransitionController` whose matrix is this observer's outcome states.
    router:
        The :class:`SurpriseRouter` implementing the no-surprise (active-inference) logic.
        Each observer owns its own router so its EWMA surprise scale is its private "window".
    children:
        Nested observers. An observer with children is a *collective* at a higher scale.
    gate:
        Optional :class:`SurpriseActionGate` — when set, risky decisions are gated through
        the Quadrature Nexus before being acted on.
    """

    name: str
    state_matrix: object  # TransitionController (duck-typed: needs .matrix)
    router: SurpriseRouter = field(default_factory=SurpriseRouter)
    children: list[Observer] = field(default_factory=list)
    gate: object | None = None
    # The observer window: a bounded record of recent decisions at this scale.
    _recent: list[SurpriseDecision] = field(default_factory=list)
    _window: int = 32

    # -- the no-surprise logic at this scale ---------------------------------

    def observe(self, surprise: float) -> SurpriseDecision:
        """Observe one surprise value through this observer's no-surprise logic.

        Records the decision in the bounded observer window and returns it.
        """
        decision = self.router.observe(surprise)
        self._recent.append(decision)
        if len(self._recent) > self._window:
            self._recent = self._recent[-self._window :]
        return decision

    @property
    def window(self) -> list[SurpriseDecision]:
        """The current observer window (recent decisions, newest last)."""
        return list(self._recent)

    # -- recursive trace / multi-scale nesting -------------------------------

    def nest(self, child: Observer) -> Observer:
        """Nest a child observer beneath this one, forming a higher-scale collective.

        Returns ``self`` to allow chaining.
        """
        if child is self:
            raise ValueError("an observer cannot nest itself")
        self.children.append(child)
        return self

    @property
    def scale(self) -> int:
        """0 for a base agent; otherwise 1 + the deepest child scale (Levin scale level)."""
        if not self.children:
            return 0
        return 1 + max(c.scale for c in self.children)

    @property
    def is_collective(self) -> bool:
        return bool(self.children)

    def walk(self) -> Iterator[Observer]:
        """Pre-order traversal of the observer tree (self first, then descendants)."""
        yield self
        for c in self.children:
            yield from c.walk()

    def agent_count(self) -> int:
        """Total observers in this subtree (the collective's membership)."""
        return sum(1 for _ in self.walk())

    def leaf_count(self) -> int:
        """Number of base agents (leaves) in this subtree."""
        return sum(1 for o in self.walk() if not o.children)

    # -- Levin cognitive light cone ------------------------------------------

    def cognitive_light_cone(
        self, diffusion: float = 1.0, temporal_horizon: float = 1.0
    ) -> CognitiveLightCone:
        """The spatio-temporal horizon of this observer (Levin 2019).

        R_c = √(D · τ · N), where N is the number of observers in the collective — a lone
        agent (N=1) reduces to Levin's R_c = √(D·τ); nesting widens the cone. ``is_collective``
        is True when this observer has children.
        """
        n = self.agent_count()
        radius = sqrt(max(0.0, diffusion) * max(0.0, temporal_horizon) * max(1, n))
        return CognitiveLightCone(
            radius=radius,
            temporal_horizon=temporal_horizon,
            agent_ids=list(range(n)),
            is_collective=self.is_collective,
        )

    # -- multi-scale binding: collective observation -------------------------

    def collective_observe(self, child_surprises: list[float]) -> SurpriseDecision:
        """Bind child surprises into a single collective decision at this scale.

        The collective attends to the **most-surprised** subsystem (max surprise) — where the
        world model has most broken down — and runs that through this observer's own
        no-surprise logic. This is the multi-scale form of epistemic value: a collective
        explores when any of its members is sufficiently surprised.

        Raises ``ValueError`` if called with no surprises.
        """
        if not child_surprises:
            raise ValueError("collective_observe needs at least one child surprise")
        return self.observe(max(child_surprises))

    # -- aggregate over the observer tree ------------------------------------

    def aggregate(self) -> dict:
        """Summarize the observer tree (mirrors recursive ExecutionTrace.aggregate)."""
        nodes = list(self.walk())
        return {
            "observer_count": len(nodes),
            "leaf_count": self.leaf_count(),
            "max_scale": self.scale,
            "is_collective": self.is_collective,
            "state_count": len(getattr(self.state_matrix, "matrix", {}) or {}),
        }

    # -- optional consensus gate ---------------------------------------------

    async def act(self, surprise: float, *, budget_available: bool = False) -> dict:
        """Observe, then (if a gate is configured) gate the decision through consensus.

        Returns ``{"decision": SurpriseDecision, "gated": GateOutcome | None}``. Without a
        gate, the decision is returned ungated (the caller decides what to do with it).
        """
        decision = self.observe(surprise)
        if self.gate is None:
            return {"decision": decision, "gated": None}
        outcome = await self.gate.gate(decision, budget_available=budget_available)
        return {"decision": decision, "gated": outcome}
