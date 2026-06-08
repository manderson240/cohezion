"""Item 114: Heterogeneous-fabric utilization + placement — report-only.

Two report-only functions for the Strix Halo heterogeneous compute fabric
{NPU, iGPU, CPU}:

``fabric_utilization``: per-engine utilization snapshot — which engines are idle
(no models loaded) vs loaded, and which are at capacity.  Surfaces under-used
silicon (verified live 2026-06-06: iGPU=3 models incl. leftover Granite, NPU=1,
**CPU=0 LLMs** → all 32 CPU threads idle for inference).

``place_task``: proposes which engine a task should run on, respecting the
engine's affinity role and skipping engines that are at capacity (spillover).

Task→Engine affinity (from Triune Orchestrator routing philosophy):
  - classify / batch  → NPU  (fast categorical, high TPS, 42 TPS on llama3.2-1b-FLM)
  - interactive       → iGPU (real-time quality, ~200ms on Gemma-4-E4B)
  - deep-reasoning / overflow → CPU (parallel / long-context, ~800ms on Gemma-4-31B)
  - unknown           → iGPU (safe middle-tier default)

Pure (injected ``loaded_models`` + ``engines``; no live lemonade probe under pytest).
Report-only — the actual model-load/placement is gated by K1/rule-5 OOM.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

# Task types and their preferred engine affinity.
_TASK_AFFINITY: dict[str, str] = {
    "classify": "npu",
    "batch": "npu",
    "interactive": "igpu",
    "deep-reasoning": "cpu",
    "overflow": "cpu",
}

# Spillover preference order when preferred engine is unavailable or at capacity.
_SPILLOVER_ORDER: list[str] = ["igpu", "npu", "cpu"]


@dataclass(frozen=True)
class EngineSpec:
    """Injected description of one compute engine (item 114).

    Attributes
    ----------
    name:
        Engine identifier: ``"npu"``, ``"igpu"``, or ``"cpu"``.
    loaded_models:
        Model names currently loaded on this engine.
    capacity:
        Maximum number of models the engine can serve simultaneously.
        Default 4 (conservative for 128 GiB shared RAM).
    """

    name: str
    loaded_models: list[str] = field(default_factory=list)
    capacity: int = 4


@dataclass(frozen=True)
class EngineInfo:
    """Per-engine utilization snapshot (item 114).

    Attributes
    ----------
    name:
        Engine identifier.
    loaded_count:
        Number of models currently loaded.
    is_idle:
        ``True`` when ``loaded_count == 0`` (no models serving).
    at_capacity:
        ``True`` when ``loaded_count >= capacity`` (no free slots).
    """

    name: str
    loaded_count: int
    is_idle: bool
    at_capacity: bool


# ---------------------------------------------------------------------------
# fabric_utilization
# ---------------------------------------------------------------------------


def fabric_utilization(engines: list[EngineSpec]) -> dict[str, EngineInfo]:
    """Report per-engine utilization for the heterogeneous fabric (item 114). READ-ONLY.

    Args:
        engines:
            List of :class:`EngineSpec` objects describing each compute engine.
            Injected — no live lemonade/lemond probe is made.

    Returns:
        Dict mapping engine ``name`` → :class:`EngineInfo`.
        Empty ``engines`` → ``{}``.

    Pure (no writes, no network calls).
    """
    return {
        e.name: EngineInfo(
            name=e.name,
            loaded_count=len(e.loaded_models),
            is_idle=len(e.loaded_models) == 0,
            at_capacity=len(e.loaded_models) >= e.capacity,
        )
        for e in engines
    }


# ---------------------------------------------------------------------------
# place_task
# ---------------------------------------------------------------------------


def place_task(
    task: str,
    *,
    engines: list[EngineSpec],
) -> str | None:
    """Propose which engine to run ``task`` on (item 114). READ-ONLY.

    Returns the preferred engine by task affinity, skipping engines that are at
    capacity (spillover).  If the preferred engine is at capacity, tries the
    remaining engines in spillover order.  Returns ``None`` when all engines are
    at capacity or no engines are provided.

    Task affinity:
    - ``"classify"`` / ``"batch"`` → ``"npu"``
    - ``"interactive"`` → ``"igpu"``
    - ``"deep-reasoning"`` / ``"overflow"`` → ``"cpu"``
    - Unknown tasks → ``"igpu"`` (safe middle-tier default).

    Args:
        task:
            Task type string.
        engines:
            List of available :class:`EngineSpec` objects.

    Returns:
        Engine name string, or ``None`` when no engine has a free slot.

    Pure (no writes, no network calls).
    """
    if not engines:
        return None

    engine_map = {e.name: e for e in engines}
    util = fabric_utilization(engines)

    preferred = _TASK_AFFINITY.get(task, "igpu")

    # Try preferred engine first, then spillover order, then anything available.
    candidate_order: list[str] = [preferred] + [e for e in _SPILLOVER_ORDER if e != preferred]
    # Also include any engine not in the canonical order (future-proofing).
    for name in engine_map:
        if name not in candidate_order:
            candidate_order.append(name)

    for name in candidate_order:
        if name not in util:
            continue
        if not util[name].at_capacity:
            return name

    return None  # all at capacity
