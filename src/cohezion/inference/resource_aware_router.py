"""Resource-aware router (user directive 2026-06-07: "we need a resource aware router").

The fleet had resource PROBING (`MemorySnapshot.capture().available_gb`,
`HardwareTelemetry.snapshot()`) and an OOM GATE (`ResourceManager.can_load_model`, the 16 GB
buffer triune enforces) — but NO router that consults live resource state to make a routing
decision. This is that piece. The gap is exactly what let a background distillation batch
saturate the fleet and make the bot reply empty (2026-06-06): nothing checked "is there room,
and where should this run, given what's free RIGHT NOW?".

`resource_aware_route` composes three existing-but-uncomposed concerns into ONE decision:
  - the K1/rule-5 OOM buffer (defer if available RAM < buffer — the gate triune uses),
  - per-task headroom (defer if the model won't fit with the can_load_model 1.2x margin),
  - item-113 fleet-fairness (a batch job yields to the NPU lane when the bot is busy),
  - item-114 placement (interactive→iGPU, batch→NPU, deep-reasoning→CPU).

Report-only at the decision layer: it returns a `RouteDecision` (action + engine + reason); it
NEVER loads a model. **As of 2026-06-07 it has a real production consumer**: `fleet.route()`
captures a memory snapshot and uses the OOM-guard branch to DEFER local lanes under memory
pressure (so a saturated fleet falls through to cloud instead of returning empty — the
2026-06-06 bot saturation). See `tests/inference/test_fleet_resource_gate.py`. Pure given an
injected snapshot — `route_now` is the thin live-capture convenience (not unit-tested against
live hardware).

Engine labels map to the triune ports: npu=13306 (via omnirouter 13305), igpu=13307, cpu=13309.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from cohezion.competition.orchestrator.resource_guard import MemorySnapshot


Engine = Literal["npu", "igpu", "cpu"]
TaskKind = Literal["interactive", "batch", "deep"]

# The OOM buffer triune enforces (triune_orchestrator.py:65 — available < 16 GB → abort).
_OOM_BUFFER_GB = 16.0
# can_load_model headroom margin (avail must exceed size * 1.2).
_HEADROOM_MARGIN = 1.2
# item-114 placement: which engine each task kind prefers.
_ENGINE_BY_KIND: dict[str, Engine] = {"interactive": "igpu", "batch": "npu", "deep": "cpu"}


@dataclass(frozen=True)
class RouteDecision:
    """A report-only routing proposal — what the dispatcher SHOULD do, not what it did."""

    action: Literal["route", "defer"]
    engine: Engine | None  # None when action == "defer"
    reason: str


def resource_aware_route(
    task_size_gb: float,
    *,
    snapshot: MemorySnapshot,
    interactive_busy: bool = False,
    task_kind: TaskKind = "batch",
    oom_buffer_gb: float = _OOM_BUFFER_GB,
) -> RouteDecision:
    """Decide where (or whether) to run a task given live memory + bot-busy state. Report-only.

    Decision order (the OOM gate dominates — a "does it fit?" check alone caused the fleet
    saturation this router prevents):
      1. ``available_gb < oom_buffer_gb`` → DEFER (loading anything risks OOM, K1/rule-5).
      2. ``available_gb < task_size_gb * 1.2`` → DEFER (won't fit with the can_load_model margin).
      3. ``interactive_busy`` and a BATCH task → route to NPU (yield the iGPU to the live bot).
      4. otherwise → the engine item-114 assigns this task kind.

    Pure: depends only on the injected ``snapshot`` and flags; loads nothing.
    """
    avail = snapshot.available_gb
    if avail < oom_buffer_gb:
        return RouteDecision(
            "defer", None, f"oom_guard: {avail:.1f} GB < {oom_buffer_gb:.1f} GB buffer"
        )
    if avail < task_size_gb * _HEADROOM_MARGIN:
        return RouteDecision(
            "defer",
            None,
            f"insufficient_headroom: {avail:.1f} GB < {task_size_gb:.1f}*{_HEADROOM_MARGIN}",
        )
    if interactive_busy and task_kind == "batch":
        return RouteDecision("route", "npu", "yield_to_interactive: batch → NPU lane")
    engine = _ENGINE_BY_KIND[task_kind]
    return RouteDecision("route", engine, f"placement: {task_kind} → {engine}")


def route_now(
    task_size_gb: float,
    *,
    interactive_busy: bool = False,
    task_kind: TaskKind = "batch",
) -> RouteDecision:
    """Live-capture convenience: capture the current memory snapshot, then decide. Not pure."""
    return resource_aware_route(
        task_size_gb,
        snapshot=MemorySnapshot.capture(),
        interactive_busy=interactive_busy,
        task_kind=task_kind,
    )
