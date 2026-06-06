"""Fleet-Routing Specialist — the local-inference front-door (item 34, thread E).

Composes three VERIFIED tools into one `route()` call, adding no new inference logic:
  - the task-TYPE classifier (item 7 / model_registry) — query → `Task`;
  - `FleetRegistry.for_task` — `Task` → registered specialists;
  - `extend_claude`'s escalation SEMANTICS (local-first → cloud only on quality-gate failure).

`route()` classifies the query, picks the cheapest LOCAL $0 specialist, and sets an `escalate`
flag ONLY when an injected local quality gate fails AND `budget_usd > 0` — the CC2 principle
($0 local beats cloud, so with no budget we never escalate). It PROPOSES a route; it never
executes inference. The classifier, gate, and budget are injectable so the decision is
deterministic and testable.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from cohezion.inference.registry import Lane, ModelEntry, Task, get_registry


_LOCAL_LANES = frozenset({Lane.NPU, Lane.IGPU_ROCWMMA, Lane.IGPU_UNIFIED, Lane.CPU})


@dataclass(frozen=True)
class RoutingDecision:
    """A proposed route. ``model_id`` is the chosen local specialist (or None → complexity-router
    fallback). ``escalate`` advises cloud ONLY when the local gate failed AND budget allowed it."""

    model_id: str | None
    lane: str | None
    task: str | None
    escalate: bool
    rationale: str


def _default_classifier(query: str) -> Task | None:
    from cohezion.models.model_registry import _classify_task

    return _classify_task(query)


class FleetRoutingSpecialist:
    """Local-inference front-door: classify → cheapest $0 local specialist → escalate-on-gate-fail."""

    def __init__(self, *, classifier: Callable[[str], Task | None] | None = None) -> None:
        self._classify = classifier or _default_classifier

    def route(
        self,
        query: str,
        *,
        budget_usd: float = 0.0,
        local_quality_gate: Callable[[ModelEntry], bool] | None = None,
    ) -> RoutingDecision:
        """Route ``query`` to a local $0 specialist; flag ``escalate`` only on gate-fail + budget.

        Unclassifiable query → complexity-router fallback (model_id=None). Classifiable but no
        local specialist → also fallback. With a local specialist, ``escalate`` is True iff
        ``local_quality_gate(best)`` is False AND ``budget_usd > 0`` (no budget ⇒ stay local).
        """
        task = self._classify(query)
        if task is None:
            return RoutingDecision(
                None, None, None, False, "unclassifiable → complexity-router fallback"
            )
        local = [
            m
            for m in get_registry().for_task(task)
            if m.lane in _LOCAL_LANES
            and m.cost_per_1k_input_usd == 0.0
            and m.cost_per_1k_output_usd == 0.0
        ]
        if not local:
            return RoutingDecision(
                None,
                None,
                task.name,
                False,
                f"{task.name}: no local $0 specialist → complexity-router fallback",
            )
        best = min(local, key=lambda m: m.priority)  # cheapest/best-fit local (priority ascending)
        gate_failed = local_quality_gate is not None and not local_quality_gate(best)
        escalate = gate_failed and budget_usd > 0
        why = f"{task.name} → {best.model_id} (local $0, {best.lane.name})"
        if escalate:
            why += " | ESCALATE: local quality gate failed AND budget>0"
        elif gate_failed:
            why += " | gate failed but budget=0 → stay local ($0 beats cloud, CC2)"
        return RoutingDecision(best.model_id, best.lane.name, task.name, escalate, why)
