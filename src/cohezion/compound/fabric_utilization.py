"""Item 114: Heterogeneous-fabric utilization + placement reporter.

``fabric_utilization`` reports, per engine (NPU / iGPU / CPU), which models are
loaded and whether the engine is IDLE or at capacity — surfacing under-used
silicon (live finding 2026-06-06: CPU = 0 LLMs loaded).

``place_task`` proposes which engine a task should run on, following the Triune
routing ladder:
    NPU   → classify / batch        (fast, cheap, 42 TPS)
    iGPU  → interactive             (~200ms, RDNA 3.5)
    CPU   → deep_reasoning          (slow, large context, 32 threads)

Report-only: the actual model-load / placement is a SEPARATE gated step subject
to the K1/rule-5 OOM gate (``free -h`` headroom check before loading any model).

Composes with:
    - ``triune_orchestrator.py``  (port mapping: NPU=13306, iGPU=13307, CPU=13309)
    - ``fleet_registry.py``       (FleetRegistry / ModelEntry for model listings)
    - item-113 ``fleet_fairness`` (yield-to-interactive predicate)
    - item-118 ``bot_tier_plan``  (bot-specific placement layer, dep: 114)

Pure (injected ``engines`` list; no live HTTP probe, no model load under pytest).
"""

from __future__ import annotations

from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Engine descriptor (injected by caller; no live probe)
# ---------------------------------------------------------------------------

# Task-kind → preferred engine kind (primary routing table)
_TASK_PREFERENCE: dict[str, str] = {
    "classify": "npu",
    "batch": "npu",
    "interactive": "igpu",
    "deep_reasoning": "cpu",
}

# Spillover order when the preferred engine is unavailable / at capacity
_SPILLOVER_ORDER: dict[str, list[str]] = {
    "npu": ["igpu", "cpu"],
    "igpu": ["cpu", "npu"],
    "cpu": ["igpu", "npu"],
}


@dataclass(frozen=True)
class Engine:
    """Snapshot of a single local inference engine (item 114).

    Attributes
    ----------
    kind:
        Engine type identifier — one of ``"npu"``, ``"igpu"``, ``"cpu"``.
    loaded_models:
        Tuple of model-id strings currently loaded on this engine.
        Empty tuple = engine is IDLE (no LLMs loaded).
    capacity:
        Maximum concurrent tasks this engine can handle.  When
        ``in_flight >= capacity`` the engine is considered *at capacity*.
    in_flight:
        Number of tasks currently running on this engine.
    """

    kind: str
    loaded_models: tuple[str, ...] = field(default_factory=tuple)
    capacity: int = 1
    in_flight: int = 0


# ---------------------------------------------------------------------------
# Utilization report
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EngineUtilization:
    """Per-engine utilization snapshot (item 114).

    Attributes
    ----------
    kind:
        Engine type identifier (forwarded from :class:`Engine`).
    loaded_models:
        List of model-id strings currently loaded (forwarded).
    is_idle:
        ``True`` when no models are loaded on this engine.
    at_capacity:
        ``True`` when ``in_flight >= capacity``.
    """

    kind: str
    loaded_models: list[str]
    is_idle: bool
    at_capacity: bool


def fabric_utilization(engines: list[Engine]) -> dict[str, EngineUtilization]:
    """Report utilization for every engine in the injected fleet (item 114). Pure.

    Args:
        engines:
            Snapshots of all available local inference engines.  Injected —
            no live HTTP probe is made under pytest.

    Returns:
        Mapping of ``engine.kind → EngineUtilization``.  Empty when
        ``engines`` is empty.  ``is_idle=True`` when no models are loaded;
        ``at_capacity=True`` when ``in_flight >= capacity``.

    Pure (no writes, no HTTP calls, no clock reads).  Report-only.
    """
    return {
        e.kind: EngineUtilization(
            kind=e.kind,
            loaded_models=list(e.loaded_models),
            is_idle=len(e.loaded_models) == 0,
            at_capacity=e.in_flight >= e.capacity,
        )
        for e in engines
    }


# ---------------------------------------------------------------------------
# Task placement proposal
# ---------------------------------------------------------------------------


def place_task(task_kind: str, *, engines: list[Engine]) -> str | None:
    """Propose which engine should run ``task_kind`` (item 114). Pure.

    Follows the Triune routing ladder (primary → spillover) and respects
    engine capacity.  Never triggers a model load — that is a gated step.

    Routing table::

        classify / batch   → NPU  (fast categorical, 42 TPS)
        interactive        → iGPU (~200ms, human-facing)
        deep_reasoning     → CPU  (long-context, 32-thread, slow)

    When the preferred engine is at capacity (``in_flight >= capacity``),
    tries each engine in spillover order until one is available.

    Args:
        task_kind:
            One of ``"classify"``, ``"batch"``, ``"interactive"``,
            ``"deep_reasoning"``.  Unknown kinds follow the iGPU default.
        engines:
            Injected fleet snapshot (same as :func:`fabric_utilization`).

    Returns:
        The ``kind`` string of the proposed engine, or ``None`` when ALL
        engines are at capacity (report-only: the caller decides to queue /
        retry / escalate).

    Pure (no writes, no HTTP calls).  Report-only.
    """
    engine_by_kind: dict[str, Engine] = {e.kind: e for e in engines}

    preferred = _TASK_PREFERENCE.get(task_kind, "igpu")

    # Build candidate order: preferred first, then spillover
    candidates = [preferred, *_SPILLOVER_ORDER.get(preferred, [])]

    for kind in candidates:
        e = engine_by_kind.get(kind)
        if e is None:
            continue  # engine not in fleet
        if e.in_flight < e.capacity:
            return kind

    return None  # all engines at capacity or not in fleet
